from dataclasses import dataclass, field
from enum import Enum
from typing import List


class ErrorCode(Enum):
    OK = 0
    FILE_NOT_FOUND = 1
    INVALID_FORMAT = 2
    UNKNOWN = 99

@dataclass
class Header:
    revMajor:int=1
    revMinor:int=4
    name:str=""
    version:str="1"
    date:str=""
    north:float=0.0
    south:float=0.0
    east:float=0.0
    west:float=0.0
    vendor:str=""
    gepreference_text:str=""

class LineType(Enum):
    LINE_STRAIGHT = 0
    CIRCULAR_ARC = 1
    SPIRAL = 2
    POLY3 = 3

@dataclass
class Line_Straight:
    length:float=0.0

@dataclass
class Line_Spiral:
    curvStart:float=0.0
    curvEnd:float=0.0

@dataclass
class Line_Poly3:
    a:float=0.0
    b:float=0.0
    c:float=0.0
    d:float=0.0

@dataclass
class Line_Arc:
    curvature:float=0.0

@dataclass
class Geometry:
    ref_line_type:LineType=LineType.LINE_STRAIGHT
    s:float=0.0 # s coordinate
    x:float=0.0 # x coordinate
    y:float=0.0 # y coordinate
    hdg:float=0.0 # heading
    length:float=0.0 # length

    straight:Line_Straight=field(default_factory=Line_Straight) # straight parameters
    spiral:Line_Spiral=field(default_factory=Line_Spiral) # spiral parameters
    poly3:Line_Poly3=field(default_factory=Line_Poly3) # poly3 parameters
    arc:Line_Arc=field(default_factory=Line_Arc) # arc parameters
    
@dataclass
class PlanView:
    geometry_list:List[Geometry]=field(default_factory=list) # geometry list

@dataclass
class Road:
    id:str = ""
    name:str = ""
    length:float = 0.0
    junction_id:str = ""
    type:str = ""
    planview:PlanView = field(default_factory=PlanView)
    elevationProfile:dict = field(default_factory=dict)
    lateralProfile:dict = field(default_factory=dict)

@dataclass
class Junction:
    id:str=""
    