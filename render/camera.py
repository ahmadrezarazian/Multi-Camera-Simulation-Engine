import math
from pyrr import Matrix44, Vector3


class OrbitCamera:
    def __init__(self, radius, height, angular_speed_deg, target, fov_deg, near, far):
        self.radius = float(radius)
        self.height = float(height)
        self.angular_speed_deg = float(angular_speed_deg)
        self.target = Vector3(target)
        self.fov_deg = float(fov_deg)
        self.near = float(near)
        self.far = float(far)

    def get_eye(self, t_seconds: float):
        angle = math.radians(self.angular_speed_deg * t_seconds)
        x = math.cos(angle) * self.radius
        z = math.sin(angle) * self.radius
        y = self.height
        return Vector3([x, y, z])

    def get_view_matrix(self, t_seconds: float):
        eye = self.get_eye(t_seconds)
        return Matrix44.look_at(eye, self.target, Vector3([0.0, 1.0, 0.0]))

    def get_projection_matrix(self, aspect_ratio: float):
        return Matrix44.perspective_projection(self.fov_deg, aspect_ratio, self.near, self.far)
