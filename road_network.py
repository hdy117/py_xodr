import os
import constants
import logging
from lxml import etree
from typing import List
import geometry_math
import matplotlib.pyplot as plt

class RoadNetwork:
    def __init__(self, xodr_file:str=""):
        self.xodr_file = xodr_file
        self.ROOT_TAG:str="OpenDRIVE"

        self.odr_doc:dict={
            'header':constants.Header(),
            'roads':[constants.Road()],
            'junctions':[constants.Junction()],
        }

        logging.info(f"RoadNetwork initialized with xodr file: {self.xodr_file}")

    def parse_xodr(self) -> int:
        # check if the file exists
        if not os.path.exists(self.xodr_file):
            logging.error(f"XODR file {self.xodr_file} not found")
            return constants.ErrorCode.FILE_NOT_FOUND
        try:
            # load the xodr file
            tree = etree.parse(self.xodr_file)
            root = tree.getroot()
            logging.debug(etree.tostring(root, pretty_print=True))
            
            # check if the file's root tag is 'OpenDRIVE'
            logging.info(f'root tag:{root.tag}')
            if root.tag != self.ROOT_TAG:
                logging.error(f"XODR file {self.xodr_file} is not a valid OpenDRIVE file")
                return constants.ErrorCode.INVALID_FILE  

            # print all elements tag
            elements = root.xpath(f'/{self.ROOT_TAG}/*')
            element_tags = [ element.tag for element in elements ]
            logging.info(f'element tags:{set(element_tags)}')

            # get header
            header_elements=root.xpath(f'/{self.ROOT_TAG}/header')
            print(f'len of header elements:{len(header_elements)}')
            header_elements_len=len(header_elements)
            if header_elements_len!=1:
                logging.error(f"XODR file {self.xodr_file} has {header_elements_len} header elements, expected 1")
                return constants.ErrorCode.INVALID_FILE
            else:
                self.odr_doc['header']=self._parse_header(header_elements)
                logging.info(f'header:{self.odr_doc["header"]}')
                
            # get roads
            road_elements=root.xpath(f'/{self.ROOT_TAG}/road')
            logging.info(f'len of road elements:{len(road_elements)}')
            if len(road_elements)==0:
                logging.error(f"XODR file {self.xodr_file} has no road elements")
                return constants.ErrorCode.INVALID_FILE
            else:
                self.odr_doc['roads']=self._parse_roads(road_elements)
                logging.info(f'len of roads parsed:{len(self.odr_doc["roads"])}')
                logging.info(f'roads[0]:{self.odr_doc["roads"][0]}')
                logging.info(f'roads[3]:{self.odr_doc["roads"][3]}')
            
            # get juntions
            junction_elements=root.xpath(f'/{self.ROOT_TAG}/junction')
            logging.info(f'len of junction elements:{len(junction_elements)}')
            if len(junction_elements)>0:
                self.odr_doc['junctions']=self._parse_junctions(junction_elements)
                logging.info(f'len of junctions parsed:{len(self.odr_doc["junctions"])}')
                logging.info(f'junctions[0]:{self.odr_doc["junctions"][0]}')

        except Exception as e:
            logging.error(f"parse xodr file {self.xodr_file} failed: {str(e)}")
            return constants.ErrorCode.UNKNOWN                                            

        return constants.ErrorCode.OK
    
    def _parse_header(self, header_elements:List[etree.Element]) -> constants.Header:
        header=constants.Header()
        
        header.revMajor=int(header_elements[0].get('revMajor'))
        header.revMinor=int(header_elements[0].get('revMinor'))
        header.name=header_elements[0].get('name')
        header.version=header_elements[0].get('version')
        header.date=header_elements[0].get('date')
        header.north=float(header_elements[0].get('north','0.0'))
        header.south=float(header_elements[0].get('south','0.0'))
        header.east=float(header_elements[0].get('east','0.0'))
        header.west=float(header_elements[0].get('west','0.0'))
        header.vendor=header_elements[0].get('vendor')

        header.gepreference_text=""
        geo_reference=header_elements[0].xpath('geoReference')
        if len(geo_reference)>=1:
            header.gepreference_text=geo_reference[0].text.strip()
        
        return header
    
    def _parse_roads(self, road_elements:List[etree.Element]) -> List[constants.Road]:
        roads:List[constants.Road] = []
        for road_element in road_elements:
            road_element_tag = road_element.tag
            # logging.info(f'road parsing:{etree.tostring(road_element, pretty_print=True)}')
            if road_element_tag != 'road':
                logging.error(f"invalid road element tag: {road_element_tag}, {etree.tostring(road_element, pretty_print=True)}")
                continue

            # create a new road instance
            road_obj = constants.Road()
            
            # get attributes
            if 'id' not in road_element.attrib:
                logging.error(f"road element {road_element_tag} has no id attribute")
                continue
            road_obj.id = road_element.get('id')
            road_obj.name = road_element.get('name', "")
            road_obj.length = float(road_element.get('length', '0.0'))
            road_obj.junction_id = road_element.get('junction', "-1")
            road_obj.type = road_element.get('type', "")

            # get planview
            planview_elements = road_element.xpath('.//planView')
            if len(planview_elements) != 1:
                logging.error(f'road id {road_obj.id} should have 1 planview element')
                continue
            else:
                planview = constants.PlanView()
                geometry_elements=planview_elements[0].xpath('.//geometry')
               
                # parse geometry elements
                for geometry_element in geometry_elements:
                    geometry=constants.Geometry()

                    # get attributes
                    geometry.s = float(geometry_element.get('s', '0.0'))
                    geometry.x = float(geometry_element.get('x', '0.0'))
                    geometry.y = float(geometry_element.get('y', '0.0'))
                    geometry.hdg = float(geometry_element.get('hdg', '0.0'))
                    geometry.length = float(geometry_element.get('length', '0.0'))
                    
                    # get line type and parameters
                    line_element=geometry_element.find('line')
                    arc_element=geometry_element.find('arc')
                    spiral_element=geometry_element.find('spiral')
                    poly3_element=geometry_element.find('poly3')
                    
                    if line_element is not None:
                        geometry.ref_line_type = constants.LineType.LINE_STRAIGHT
                        geometry.straight.length= geometry.length
                    elif arc_element is not None:
                        geometry.ref_line_type = constants.LineType.CIRCULAR_ARC
                        geometry.arc.curvature=float(arc_element.get('curvature', '0.0'))
                    elif spiral_element is not None:
                        geometry.ref_line_type = constants.LineType.SPIRAL
                        geometry.spiral.curvStart=float(spiral_element.get('curvStart', '0.0'))
                        geometry.spiral.curvEnd=float(spiral_element.get('curvEnd', '0.0'))
                    elif poly3_element is not None:
                        geometry.ref_line_type = constants.LineType.POLY3
                        geometry.poly3.a=float(poly3_element.get('a', '0.0'))
                        geometry.poly3.b=float(poly3_element.get('b', '0.0'))
                        geometry.poly3.c=float(poly3_element.get('c', '0.0'))
                        geometry.poly3.d=float(poly3_element.get('d', '0.0'))
                    
                    planview.geometry_list.append(geometry)
                
                road_obj.planview = planview
            
            # check if the road has at least 1 geometry element
            if len(road_obj.planview.geometry_list) == 0:
                logging.error(f'road id {road_obj.id} should have at least 1 geometry element')
                continue
            
            roads.append(road_obj)
        return roads
    
    def _parse_junctions(self, junction_elements:List[etree.Element]) -> List[constants.Junction]:
        junctions:List[constants.Junction] = []
        for junction_element in junction_elements:
            junction_element_tag = junction_element.tag
            if junction_element_tag != 'junction':
                logging.error(f"invalid junction element tag: {junction_element_tag}, {etree.tostring(junction_element, pretty_print=True)}")
                continue

            # get attributes
            junction_obj = constants.Junction()
            if 'id' not in junction_element.attrib:
                logging.error(f"junction element {junction_element_tag} has no id attribute")
                continue
            junction_obj.id = junction_element.get('id')
            junction_obj.name = junction_element.get('name', "")

            # get connections
            connection_elements=junction_element.xpath('.//connection')
            for connection_element in connection_elements:
                # get connection attributes
                connection=constants.Connection()
                connection.id=connection_element.get('id')
                connection.name=connection_element.get('name', "")
                connection.incomming_road_id=connection_element.get('incomingRoad', "")
                connection.connecting_road_id=connection_element.get('connectingRoad', "")
                connection.contact_point=connection_element.get('contactPoint', "")

                # get lane links
                lane_link_elements=connection_element.xpath('.//laneLink')
                for lane_link_element in lane_link_elements:
                    lane_link=constants.LaneLink()
                    lane_link.from_lane_id=lane_link_element.get('from', "")
                    lane_link.to_lane_id=lane_link_element.get('to', "")
                    connection.lane_links.append(lane_link)

                junction_obj.connections.append(connection)

            junctions.append(junction_obj)
        return junctions
           
    def sample_roads(self, delta_step:float=0.1):
        x_list=[]
        y_list=[]
        for road in self.odr_doc['roads']:    
            # sample refline of a road, from st coordinates to xy coordinates
            for geometry in road.planview.geometry_list:
                if geometry.ref_line_type == constants.LineType.LINE_STRAIGHT:
                    s=0.0
                    s_max=geometry.length
                    while s < s_max:
                        x,y=geometry_math.st_to_xy_line(s,0.0,geometry.x,geometry.y,geometry.hdg,geometry.length)
                        s+=delta_step
                        point_3d=constants.Point3d()
                        point_3d.x=x
                        point_3d.y=y
                        point_3d.z=0.0
                        geometry.refline_sample_points.append(point_3d)
                        x_list.append(x)
                        y_list.append(y)
                elif geometry.ref_line_type == constants.LineType.CIRCULAR_ARC:
                    s=0.0
                    s_max=geometry.length
                    while s < s_max:
                        x,y=geometry_math.st_to_xy_arc(s,0.0,geometry.x,geometry.y,geometry.hdg,geometry.arc.curvature,geometry.length)
                        s+=delta_step
                        point_3d=constants.Point3d()
                        point_3d.x=x
                        point_3d.y=y
                        point_3d.z=0.0
                        geometry.refline_sample_points.append(point_3d)
                        x_list.append(x)
                        y_list.append(y)
                elif geometry.ref_line_type == constants.LineType.SPIRAL:
                    s=0.0
                    s_max=geometry.length
                    while s < s_max:
                        x,y=geometry_math.st_to_xy_spiral(s,0.0,geometry.x,geometry.y,geometry.hdg,geometry.length,geometry.spiral.curvStart,geometry.spiral.curvEnd)
                        s+=delta_step
                        point_3d=constants.Point3d()
                        point_3d.x=x
                        point_3d.y=y
                        point_3d.z=0.0
                        geometry.refline_sample_points.append(point_3d) 
                        x_list.append(x)
                        y_list.append(y)
                elif geometry.ref_line_type == constants.LineType.POLY3:
                    raise NotImplementedError(f"Poly3 is not implemented for road {road.id}")
                   
        # plot sample points of all roads
        logging.info(f'len of x_list:{len(x_list)}, len of y_list:{len(y_list)}')
        plt.scatter(
            x_list, y_list,
            s=2,           # 控制点的大小
            c='red',       # 控制点的颜色
            alpha=0.7      # 可选：点的透明度
        )
        plt.show()


