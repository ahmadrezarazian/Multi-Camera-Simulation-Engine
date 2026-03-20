import numpy as np
from OpenGL.GL import *
from OpenGL.GL import shaders
import glfw
import cv2
from pyrr import Matrix44, Vector3


class Renderer_test:
    def __init__(self, settings):
        app = settings["app"]
        self.width = int(app["width"])
        self.height = int(app["height"])

    def render_frame(self):
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        img[:, :, 0] = 255  # Red
        return img
    


class Renderer:
    def __init__(self, settings):
        app = settings["app"]
        self.width = int(app["width"])
        self.height = int(app["height"])

        if not glfw.init(): raise Exception("GLFW initialization failed")
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        self.window = glfw.create_window(self.width, self.height, "Hidden", None, None)
        glfw.make_context_current(self.window)

        # 1. SHADERS (Directional Lighting)
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
        uniform vec3 lightDir; // Constant direction for all fragments
        uniform int is_ground;
        out vec4 out_color;
        void main() {
            vec3 lightColor = vec3(1.0, 1.0, 1.0);
            vec3 objectColor = (is_ground == 1) ? 
                (mod(floor(v_fragPos.x*2.0) + floor(v_fragPos.z*2.0), 2.0) < 1.0 ? vec3(0.2) : vec3(0.8)) : 
                vec3(0.0, 0.8, 1.0);

            // Ambient
            float ambientStr = 0.3;
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

        # 2. GEOMETRY
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

        # 3. FBO SETUP
        self.fbo = glGenFramebuffers(1); glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        self.tex = glGenTextures(1); glBindTexture(GL_TEXTURE_2D, self.tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.width, self.height, 0, GL_RGB, GL_UNSIGNED_BYTE, None)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.tex, 0)
        self.depth_rb = glGenRenderbuffers(1); glBindRenderbuffer(GL_RENDERBUFFER, self.depth_rb)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT, self.width, self.height)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, self.depth_rb)

        glfw.make_context_current(None)
        self.init_done=True
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
        if not self.init_done or self.init_done is None:
            print("Renderer not initialized properly.")
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        glfw.make_context_current(self.window)
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glEnable(GL_DEPTH_TEST)
        glViewport(0, 0, self.width, self.height)
        glClearColor(1.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(self.shader)
        
        # Camera
        time = glfw.get_time()
        cam_pos = Vector3([np.sin(time/2)*4, 2.0, np.cos(time/2)*4])
        proj = Matrix44.perspective_projection(45.0, self.width/self.height, 0.1, 100.0)
        view = Matrix44.look_at(cam_pos, Vector3([0,0,0]), Vector3([0,1,0]))

        # --- DIRECTIONAL LIGHT LOGIC ---
        # Fixed light position for now, targets 0,0,0
        light_pos = Vector3([1.0, 2.0, 3.0])
        target_pos = Vector3([0.0, 0.0, 0.0])
        # Direction is from light toward target
        # 1. Calculate the raw direction vector
        raw_direction = target_pos - light_pos
        
        # 2. Normalize the vector so its length is exactly 1.0
        # This ensures lighting intensity is consistent regardless of light distance
        light_direction = raw_direction / np.linalg.norm(raw_direction)
        
        glUniform3fv(glGetUniformLocation(self.shader, "lightDir"), 1, light_direction.astype(np.float32))
        glUniform3fv(glGetUniformLocation(self.shader, "viewPos"), 1, cam_pos.astype(np.float32))
        glUniformMatrix4fv(glGetUniformLocation(self.shader, "proj"), 1, GL_FALSE, proj.astype(np.float32))
        glUniformMatrix4fv(glGetUniformLocation(self.shader, "view"), 1, GL_FALSE, view.astype(np.float32))

        # Ground
        glUniform1i(glGetUniformLocation(self.shader, "is_ground"), 1)
        glUniformMatrix4fv(glGetUniformLocation(self.shader, "model"), 1, GL_FALSE, np.identity(4, dtype=np.float32))
        glBindVertexArray(self.ground_vao); glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)

        # Box
        glUniform1i(glGetUniformLocation(self.shader, "is_ground"), 0)
        glUniformMatrix4fv(glGetUniformLocation(self.shader, "model"), 1, GL_FALSE, np.identity(4, dtype=np.float32))
        glBindVertexArray(self.cube_vao); glDrawElements(GL_TRIANGLES, 36, GL_UNSIGNED_INT, None)

        # Export BGR
        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        data = glReadPixels(0, 0, self.width, self.height, GL_RGB, GL_UNSIGNED_BYTE)
        img_rgb = np.frombuffer(data, dtype=np.uint8).reshape((self.height, self.width, 3))
        img_bgr = cv2.cvtColor(np.flipud(img_rgb), cv2.COLOR_RGB2BGR)
        
        # Save Debug
        cv2.imwrite('frame_denug.jpg', img_bgr)
        
        glfw.make_context_current(None)
        return img_bgr



    def __init__(self, settings):
        app = settings["app"]
        self.width = int(app["width"])
        self.height = int(app["height"])
        self.init_done = False
        
        # 1. Create a Lock to prevent multiple threads from touching the GPU at once
        self.render_lock = threading.Lock()

        if not glfw.init():
            raise Exception("GLFW initialization failed")
        
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        self.window = glfw.create_window(self.width, self.height, "Hidden", None, None)
        
        # Initialize context on the main thread
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
        uniform int is_ground;
        out vec4 out_color;
        void main() {
            vec3 lightColor = vec3(1.0, 1.0, 1.0);
            vec3 objectColor = (is_ground == 1) ? 
                (mod(floor(v_fragPos.x*2.0) + floor(v_fragPos.z*2.0), 2.0) < 1.0 ? vec3(0.2) : vec3(0.8)) : 
                vec3(0.0, 0.8, 1.0);

            float ambientStr = 0.3;
            vec3 ambient = ambientStr * lightColor;
            
            vec3 norm = normalize(v_normal);
            vec3 negLightDir = normalize(-lightDir);
            float diff = max(dot(norm, negLightDir), 0.0);
            vec3 diffuse = diff * lightColor;
            
            float specStr = 0.5;
            vec3 viewDir = normalize(viewPos - v_fragPos);
            vec3 reflectDir = reflect(normalize(lightDir), norm);  
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
            -0.5,-0.5, 0.5, 0,0,1,  0.5,-0.5, 0.5, 0,0,1,  0.5, 0.5, 0.5, 0,0,1, -0.5, 0.5, 0.5, 0,0,1,
            -0.5,-0.5,-0.5, 0,0,-1, 0.5,-0.5,-0.5, 0,0,-1, 0.5, 0.5,-0.5, 0,0,-1, -0.5, 0.5,-0.5, 0,0,-1,
             0.5,-0.5, 0.5, 1,0,0,  0.5,-0.5,-0.5, 1,0,0,  0.5, 0.5,-0.5, 1,0,0,  0.5, 0.5, 0.5, 1,0,0,
            -0.5,-0.5, 0.5,-1,0,0, -0.5,-0.5,-0.5,-1,0,0, -0.5, 0.5,-0.5,-1,0,0, -0.5, 0.5, 0.5,-1,0,0,
            -0.5, 0.5, 0.5, 0,1,0,  0.5, 0.5, 0.5, 0,1,0,  0.5, 0.5,-0.5, 0,1,0, -0.5, 0.5,-0.5, 0,1,0,
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
        
        # 2. Use the Lock. If another request is rendering, this thread will WAIT.
        with self.render_lock:
            glfw.make_context_current(self.window)
            try:
                glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
                glEnable(GL_DEPTH_TEST)
                glViewport(0, 0, self.width, self.height)
                glClearColor(0.1, 0.1, 0.6, 1.0)
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

                glUseProgram(self.shader)
                
                # Camera
                time = glfw.get_time()
                cam_pos = Vector3([np.sin(time/2)*4, 2.0, np.cos(time/2)*4])
                proj = Matrix44.perspective_projection(45.0, self.width/self.height, 0.1, 100.0)
                view = Matrix44.look_at(cam_pos, Vector3([0,0,0]), Vector3([0,1,0]))

                # Lighting
                light_pos = Vector3([1.0, 2.0, 3.0])
                target_pos = Vector3([0.0, 0.0, 0.0])
                light_dir = (target_pos - light_pos)
                light_dir = light_dir / np.linalg.norm(light_dir)
                
                glUniform3fv(glGetUniformLocation(self.shader, "lightDir"), 1, light_dir.astype(np.float32))
                glUniform3fv(glGetUniformLocation(self.shader, "viewPos"), 1, cam_pos.astype(np.float32))
                glUniformMatrix4fv(glGetUniformLocation(self.shader, "proj"), 1, GL_FALSE, proj.astype(np.float32))
                glUniformMatrix4fv(glGetUniformLocation(self.shader, "view"), 1, GL_FALSE, view.astype(np.float32))

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
                
                return img_bgr

            finally:
                # 3. Always release context so it can be picked up by the next thread
                glfw.make_context_current(None)