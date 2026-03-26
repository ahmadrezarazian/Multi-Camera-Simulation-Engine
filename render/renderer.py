import numpy as np
from OpenGL.GL import *
from OpenGL.GL import shaders
import glfw
import cv2
import ctypes
import threading
from pyrr import Matrix44, Vector3
import math

class Renderer:
    def __init__(self, settings):
        self.settings = settings  # Store settings as an instance variable
        self.width = int(settings["app"]["width"])
        self.height = int(settings["app"]["height"])
        self.init_done = False
        
        self.render_lock = threading.Lock()

        if not glfw.init():
            raise Exception("GLFW initialization failed")
        
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        self.window = glfw.create_window(self.width, self.height, "Hidden", None, None)
        
        glfw.make_context_current(self.window)

        # --- SHADER SETUP ---
        VERTEX_SHADER = """
        #version 330
        layout(location = 0) in vec3 position;
        layout(location = 1) in vec3 normal;
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 proj;
        out vec3 v_normal;
        out vec3 v_fragPos;
        void main() {
            v_fragPos = vec3(model * vec4(position, 1.0));
            v_normal = mat3(transpose(inverse(model))) * normal;
            gl_Position = proj * view * vec4(v_fragPos, 1.0);
        }
        """
        FRAGMENT_SHADER = """
        #version 330
        in vec3 v_normal;
        in vec3 v_fragPos;
        uniform vec3 viewPos;
        uniform vec3 lightDir;
        uniform float ambientStr; // Added ambientStr uniform
        uniform int is_ground;
        out vec4 out_color;
        void main() {
            vec3 lightColor = vec3(1.0, 1.0, 1.0);
            vec3 objectColor = (is_ground == 1) ? 
                (mod(floor(v_fragPos.x*2.0) + floor(v_fragPos.z*2.0), 2.0) < 1.0 ? vec3(0.2) : vec3(0.8)) : 
                vec3(0.0, 0.8, 1.0);

            // Ambient
            vec3 ambient = ambientStr * lightColor;
            
            // Diffuse (Directional)
            vec3 norm = normalize(v_normal);
            vec3 negLightDir = normalize(-lightDir); // Direction toward light
            float diff = max(dot(norm, negLightDir), 0.0);
            vec3 diffuse = diff * lightColor;
            
            // Specular
            float specStr = 0.5;
            vec3 viewDir = normalize(viewPos - v_fragPos);
            vec3 reflectDir = reflect(lightDir, norm);  
            float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32);
            vec3 specular = specStr * spec * lightColor;  
            
            out_color = vec4((ambient + diffuse + specular) * objectColor, 1.0);
        }
        """
        self.shader = shaders.compileProgram(
            shaders.compileShader(VERTEX_SHADER, GL_VERTEX_SHADER),
            shaders.compileShader(FRAGMENT_SHADER, GL_FRAGMENT_SHADER)
        )

        # --- GEOMETRY SETUP ---
        cube_data = np.array([
            # Front             # Normals
            -0.5,-0.5, 0.5, 0,0,1,  0.5,-0.5, 0.5, 0,0,1,  0.5, 0.5, 0.5, 0,0,1, -0.5, 0.5, 0.5, 0,0,1,
            # Back
            -0.5,-0.5,-0.5, 0,0,-1, 0.5,-0.5,-0.5, 0,0,-1, 0.5, 0.5,-0.5, 0,0,-1, -0.5, 0.5,-0.5, 0,0,-1,
            # Right
             0.5,-0.5, 0.5, 1,0,0,  0.5,-0.5,-0.5, 1,0,0,  0.5, 0.5,-0.5, 1,0,0,  0.5, 0.5, 0.5, 1,0,0,
            # Left
            -0.5,-0.5, 0.5,-1,0,0, -0.5,-0.5,-0.5,-1,0,0, -0.5, 0.5,-0.5,-1,0,0, -0.5, 0.5, 0.5,-1,0,0,
            # Top
            -0.5, 0.5, 0.5, 0,1,0,  0.5, 0.5, 0.5, 0,1,0,  0.5, 0.5,-0.5, 0,1,0, -0.5, 0.5,-0.5, 0,1,0,
            # Bottom
            -0.5,-0.5, 0.5, 0,-1,0, 0.5,-0.5, 0.5, 0,-1,0, 0.5,-0.5,-0.5, 0,-1,0, -0.5,-0.5,-0.5, 0,-1,0
        ], dtype=np.float32)
        
        cube_indices = np.array([
            0,1,2, 2,3,0, 4,5,6, 6,7,4, 8,9,10, 10,11,8, 12,13,14, 14,15,12, 16,17,18, 18,19,16, 20,21,22, 22,23,20
        ], dtype=np.uint32)

        ground_data = np.array([
            -10,-0.5,-10, 0,1,0,  10,-0.5,-10, 0,1,0,  10,-0.5,10, 0,1,0, -10,-0.5,10, 0,1,0
        ], dtype=np.float32)
        ground_indices = np.array([0,1,2, 2,3,0], dtype=np.uint32)

        self.cube_vao = self._create_vao(cube_data, cube_indices)
        self.ground_vao = self._create_vao(ground_data, ground_indices)

        # --- FBO SETUP ---
        self.fbo = glGenFramebuffers(1); glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        self.tex = glGenTextures(1); glBindTexture(GL_TEXTURE_2D, self.tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.width, self.height, 0, GL_RGB, GL_UNSIGNED_BYTE, None)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.tex, 0)
        self.depth_rb = glGenRenderbuffers(1); glBindRenderbuffer(GL_RENDERBUFFER, self.depth_rb)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT, self.width, self.height)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, self.depth_rb)

        glfw.make_context_current(None)
        self.init_done = True
        print("Renderer initialized successfully.")

    def _create_vao(self, data, indices):
        vao = glGenVertexArrays(1); glBindVertexArray(vao)
        vbo = glGenBuffers(1); glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_STATIC_DRAW)
        ebo = glGenBuffers(1); glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 24, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 24, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)
        return vao

    def render_frame(self):
        if not self.init_done:
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)
           
        with self.render_lock:
            glfw.make_context_current(self.window)
            try:
                glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
                glEnable(GL_DEPTH_TEST)
                glViewport(0, 0, self.width, self.height)

                # Get background color from settings
                bg_color = self.settings["scene"]["background_color"]
                glClearColor(bg_color[0], bg_color[1], bg_color[2], 1.0)
                #glClearColor(1.0, 0.0, 0.0, 1.0)  # Red background for debugging
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

                glUseProgram(self.shader)
                
                # Camera settings
                camera_settings = self.settings["scene"]["camera"]
                motion_delay = camera_settings["motion_delay"]
                time = glfw.get_time()
                app_fps = self.settings["app"]["fps"]
                if camera_settings["motion_type"] == "AutoRotateOnTarget":
                    camera_time = motion_delay + time
                    orbit_radius = math.sqrt((camera_settings["position"][0] - camera_settings["target"][0])**2 + (camera_settings["position"][1] - camera_settings["target"][1])**2 + (camera_settings["position"][2] - camera_settings["target"][2])**2)
                    orbit_height = camera_settings["position"][1]
                    angular_speed_deg = camera_settings["motion_speed"] 
                    camera_angle = camera_time * angular_speed_deg
                    camera_angle_rad = np.radians(camera_angle)
                    cam_pos = Vector3([np.sin(camera_angle_rad) * orbit_radius, orbit_height, np.cos(camera_angle_rad) * orbit_radius])
                else: # "Off"
                    cam_pos = Vector3(camera_settings["position"])

                target_pos = Vector3(camera_settings["target"])
                up_vector = Vector3(camera_settings["up"])

                fov = camera_settings["fov"]
                near_clip = camera_settings["near_clip"]
                far_clip = camera_settings["far_clip"]
                aspect_ratio = float(self.width) / float(self.height) # Always calculate based on current framebuffer size

                proj = Matrix44.perspective_projection(fov, aspect_ratio, near_clip, far_clip)
                view = Matrix44.look_at(cam_pos, target_pos, up_vector)

                # Lighting settings
                light_settings = self.settings["scene"]["light"]
                light_pos = Vector3(light_settings["position"])
                light_target = Vector3(light_settings["target"])
                light_direction = (light_target - light_pos)
                light_direction = light_direction / np.linalg.norm(light_direction) # Normalize for directional light
                
                # Update uniform values
                glUniform3fv(glGetUniformLocation(self.shader, "lightDir"), 1, light_direction.astype(np.float32))
                glUniform3fv(glGetUniformLocation(self.shader, "viewPos"), 1, cam_pos.astype(np.float32))
                glUniformMatrix4fv(glGetUniformLocation(self.shader, "proj"), 1, GL_FALSE, proj.astype(np.float32))
                glUniformMatrix4fv(glGetUniformLocation(self.shader, "view"), 1, GL_FALSE, view.astype(np.float32))
                glUniform1f(glGetUniformLocation(self.shader, "ambientStr"), float(self.settings["scene"]["ambient"])) # Ambient strength

                # Ground
                glUniform1i(glGetUniformLocation(self.shader, "is_ground"), 1)
                glUniformMatrix4fv(glGetUniformLocation(self.shader, "model"), 1, GL_FALSE, np.identity(4, dtype=np.float32))
                glBindVertexArray(self.ground_vao)
                glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)

                # Box
                glUniform1i(glGetUniformLocation(self.shader, "is_ground"), 0)
                glUniformMatrix4fv(glGetUniformLocation(self.shader, "model"), 1, GL_FALSE, np.identity(4, dtype=np.float32))
                glBindVertexArray(self.cube_vao)
                glDrawElements(GL_TRIANGLES, 36, GL_UNSIGNED_INT, None)

                # Read Pixels
                glPixelStorei(GL_PACK_ALIGNMENT, 1)
                data = glReadPixels(0, 0, self.width, self.height, GL_RGB, GL_UNSIGNED_BYTE)
                img_rgb = np.frombuffer(data, dtype=np.uint8).reshape((self.height, self.width, 3))
                img_bgr = cv2.cvtColor(np.flipud(img_rgb), cv2.COLOR_RGB2BGR)
                
                # Save Debug
                cv2.imwrite("frame_render_frame.png", img_bgr)
                
                return img_bgr

            finally:
                glfw.make_context_current(None)
