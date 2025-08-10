import numpy as np
from scipy.special import fresnel
from scipy.optimize import minimize_scalar

# 通用的 t 偏移函数（参考点 + 横向偏移）
def apply_t_offset(x_ref, y_ref, hdg_ref, t):
    normal = hdg_ref + np.pi / 2  # 正 t 向左
    x = x_ref + t * np.cos(normal)
    y = y_ref + t * np.sin(normal)
    return x, y

# 通用的 signed t 计算（从 xy 到参考点）
def compute_signed_t(x, y, x_ref, y_ref, hdg_ref):
    normal = hdg_ref + np.pi / 2
    dx = x - x_ref
    dy = y - y_ref
    t = dx * np.cos(normal) + dy * np.sin(normal)
    return t

### 单段函数（从之前代码复制并稍作调整）

def st_to_xy_line(s, t, x0, y0, hdg0, length):
    if not (0 <= s <= length):
        raise ValueError("s must be between 0 and length")
    x_ref = x0 + s * np.cos(hdg0)
    y_ref = y0 + s * np.sin(hdg0)
    hdg_ref = hdg0
    return apply_t_offset(x_ref, y_ref, hdg_ref, t)

def xy_to_st_line(x, y, x0, y0, hdg0, length):
    cos_h = np.cos(hdg0)
    sin_h = np.sin(hdg0)
    dx = x - x0
    dy = y - y0
    s = dx * cos_h + dy * sin_h
    t_proj = -dx * sin_h + dy * cos_h  # normal = (-sin, cos)
    s = np.clip(s, 0, length)
    x_ref = x0 + s * cos_h
    y_ref = y0 + s * sin_h
    t = compute_signed_t(x, y, x_ref, y_ref, hdg0)
    dist = (x - x_ref)**2 + (y - y_ref)**2
    return s, t, dist

def st_to_xy_arc(s, t, x0, y0, hdg0, curvature, length):
    c = curvature
    if np.abs(c) < 1e-6:
        return st_to_xy_line(s, t, x0, y0, hdg0, length)
    theta = s * c
    hdg_ref = hdg0 + theta
    sin_hdg = np.sin(hdg_ref)
    cos_hdg = np.cos(hdg_ref)
    sin_hdg0 = np.sin(hdg0)
    cos_hdg0 = np.cos(hdg0)
    x_ref = x0 + (sin_hdg - sin_hdg0) / c
    y_ref = y0 + (cos_hdg0 - cos_hdg) / c
    return apply_t_offset(x_ref, y_ref, hdg_ref, t)

def xy_to_st_arc(x, y, x0, y0, hdg0, curvature, length):
    c = curvature
    if np.abs(c) < 1e-6:
        return xy_to_st_line(x, y, x0, y0, hdg0, length)[:2], 0  # 调整返回
    r = 1.0 / np.abs(c)
    cx = x0 - np.sin(hdg0) / c
    cy = y0 + np.cos(hdg0) / c
    vec = np.array([x - cx, y - cy])
    dist_to_center = np.linalg.norm(vec)
    if dist_to_center < 1e-6:
        return 0.0, 0.0, 0.0
    proj_x = cx + vec[0] / dist_to_center * r
    proj_y = cy + vec[1] / dist_to_center * r
    vec_to_center = np.array([cx - proj_x, cy - proj_y])
    dir_center = np.arctan2(vec_to_center[1], vec_to_center[0])
    hdg_proj = dir_center - np.sign(c) * np.pi / 2
    hdg_proj = (hdg_proj + np.pi) % (2 * np.pi) - np.pi
    theta = hdg_proj - hdg0
    theta = (theta + np.pi) % (2 * np.pi) - np.pi
    s_proj = theta / c
    total_angle = length * c
    if 0 <= s_proj <= length and np.sign(theta) == np.sign(c):
        x_ref, y_ref = proj_x, proj_y
        hdg_ref = hdg_proj
        s = s_proj
    else:
        x_start, y_start = st_to_xy_arc(0, 0, x0, y0, hdg0, curvature, length)
        x_end, y_end = st_to_xy_arc(length, 0, x0, y0, hdg0, curvature, length)
        dist_start = (x - x_start)**2 + (y - y_start)**2
        dist_end = (x - x_end)**2 + (y - y_end)**2
        if dist_start <= dist_end:
            s, x_ref, y_ref, hdg_ref = 0, x_start, y_start, hdg0
        else:
            s, x_ref, y_ref, hdg_ref = length, x_end, y_end, hdg0 + total_angle
    t = compute_signed_t(x, y, x_ref, y_ref, hdg_ref)
    dist = (x - x_ref)**2 + (y - y_ref)**2
    return s, t, dist

class EulerSpiral:
    def __init__(self, gamma):
        self.gamma = gamma

    @staticmethod
    def create_from_length_and_curvature(length, curv_start, curv_end):
        if length == 0:
            return EulerSpiral(0)
        return EulerSpiral((curv_end - curv_start) / length)

    def calc_position(self, s, x0=0.0, y0=0.0, hdg0=0.0, curv0=0.0):
        if self.gamma == 0 and curv0 == 0:
            x_ref = x0 + s * np.cos(hdg0)
            y_ref = y0 + s * np.sin(hdg0)
            hdg_ref = hdg0
        elif self.gamma == 0:
            return st_to_xy_arc(s, 0, x0, y0, hdg0, curv0, s)[0], st_to_xy_arc(s, 0, x0, y0, hdg0, curv0, s)[1], hdg0 + s * curv0
        else:
            scale = np.sqrt(np.pi / np.abs(self.gamma))
            Sa, Ca = fresnel((curv0 + self.gamma * s) / scale)
            Sb, Cb = fresnel(curv0 / scale)
            sign_gamma = np.sign(self.gamma)
            Cs = np.sqrt(np.pi / np.abs(self.gamma)) * (Ca - Cb + 1j * sign_gamma * (Sa - Sb)) * np.exp(1j * hdg0) * sign_gamma
            x_ref = x0 + Cs.real
            y_ref = y0 + Cs.imag
            hdg_ref = self.gamma * s**2 / 2 + curv0 * s + hdg0
        return x_ref, y_ref, hdg_ref

def st_to_xy_spiral(s, t, x0, y0, hdg0, length, curv_start, curv_end):
    if not (0 <= s <= length):
        raise ValueError("s must be between 0 and length")
    spiral = EulerSpiral.create_from_length_and_curvature(length, curv_start, curv_end)
    x_ref, y_ref, hdg_ref = spiral.calc_position(s, x0, y0, hdg0, curv_start)
    return apply_t_offset(x_ref, y_ref, hdg_ref, t)

def xy_to_st_spiral(x, y, x0, y0, hdg0, length, curv_start, curv_end):
    spiral = EulerSpiral.create_from_length_and_curvature(length, curv_start, curv_end)
    def dist_func(s):
        x_ref, y_ref, _ = spiral.calc_position(s, x0, y0, hdg0, curv_start)
        return (x - x_ref)**2 + (y - y_ref)**2
    res = minimize_scalar(dist_func, bounds=(0, length), method='bounded')
    s_min = res.x
    x_ref, y_ref, hdg_ref = spiral.calc_position(s_min, x0, y0, hdg0, curv_start)
    t = compute_signed_t(x, y, x_ref, y_ref, hdg_ref)
    dist = res.fun
    return s_min, t, dist

### 多段处理

# 几何段定义：列表 of dicts，每个dict有 'type', 'length', 和类型特定参数
# 必须按顺序，第一个段的 x0, y0, hdg0 是道路起点
# 后续段的 x0, y0, hdg0 由上一个计算得到
def build_road_geometries(geoms):
    road_geoms = []
    s_cum = 0.0
    x_prev, y_prev, hdg_prev = geoms[0]['x0'], geoms[0]['y0'], geoms[0]['hdg0']
    for g in geoms:
        g_copy = g.copy()
        g_copy['s0'] = s_cum
        g_copy['x0'] = x_prev
        g_copy['y0'] = y_prev
        g_copy['hdg0'] = hdg_prev
        road_geoms.append(g_copy)
        # 计算下一个起点
        if g['type'] == 'line':
            x_prev, y_prev = st_to_xy_line(g['length'], 0, x_prev, y_prev, hdg_prev, g['length'])
            hdg_prev = hdg_prev
        elif g['type'] == 'arc':
            x_prev, y_prev = st_to_xy_arc(g['length'], 0, x_prev, y_prev, hdg_prev, g['curvature'], g['length'])
            hdg_prev += g['length'] * g['curvature']
        elif g['type'] == 'spiral':
            x_prev, y_prev = st_to_xy_spiral(g['length'], 0, x_prev, y_prev, hdg_prev, g['length'], g['curv_start'], g['curv_end'])
            hdg_prev += g['length']**2 * (g['curv_end'] - g['curv_start']) / (2 * g['length']) + g['curv_start'] * g['length']
        s_cum += g['length']
    for road_geom in road_geoms:
        print(f'road_geom:{road_geom}')
    return road_geoms

def st_to_xy_multi(s, t, road_geoms):
    total_length = sum(g['length'] for g in road_geoms)
    if not (0 <= s <= total_length):
        raise ValueError("s must be between 0 and total_length")
    for g in road_geoms:
        if g['s0'] <= s < g['s0'] + g['length']:
            s_local = s - g['s0']
            if g['type'] == 'line':
                return st_to_xy_line(s_local, t, g['x0'], g['y0'], g['hdg0'], g['length'])
            elif g['type'] == 'arc':
                return st_to_xy_arc(s_local, t, g['x0'], g['y0'], g['hdg0'], g['curvature'], g['length'])
            elif g['type'] == 'spiral':
                return st_to_xy_spiral(s_local, t, g['x0'], g['y0'], g['hdg0'], g['length'], g['curv_start'], g['curv_end'])
    raise ValueError("Segment not found")

def xy_to_st_multi(x, y, road_geoms):
    min_dist = float('inf')
    best_s = 0.0
    best_t = 0.0
    for g in road_geoms:
        if g['type'] == 'line':
            s_local, t_local, dist = xy_to_st_line(x, y, g['x0'], g['y0'], g['hdg0'], g['length'])
        elif g['type'] == 'arc':
            s_local, t_local, dist = xy_to_st_arc(x, y, g['x0'], g['y0'], g['hdg0'], g['curvature'], g['length'])
        elif g['type'] == 'spiral':
            s_local, t_local, dist = xy_to_st_spiral(x, y, g['x0'], g['y0'], g['hdg0'], g['length'], g['curv_start'], g['curv_end'])
        if dist < min_dist:
            min_dist = dist
            best_s = g['s0'] + s_local
            best_t = t_local
    return best_s, best_t

# 示例使用
if __name__ == "__main__":
    # 定义道路几何：不包括 s0, x0, y0, hdg0（将自动计算）
    geoms = [
        {'type': 'line', 'x0': 0.0, 'y0': 0.0, 'hdg0': 0.0, 'length': 10.0},
        {'type': 'arc', 'curvature': 0.1, 'length': 5.0},
        {'type': 'spiral', 'curv_start': 0.1, 'curv_end': 0.2, 'length': 8.0}
    ]
    road_geoms = build_road_geometries(geoms)
    
    # st to xy
    x, y = st_to_xy_multi(12.0, 1.0, road_geoms)  # s=12 在第二个段 (arc) 的 s_local=2.0
    print("Multi st(12,1) -> xy:", x, y)
    
    # xy to st
    s, t = xy_to_st_multi(x, y, road_geoms)
    print("Multi xy -> st:", s, t)