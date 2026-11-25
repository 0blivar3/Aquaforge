from __future__ import annotations

import ctypes
import math
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QMatrix4x4, QVector3D
from PySide6.QtOpenGL import QOpenGLShader, QOpenGLShaderProgram
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from OpenGL.GL import (
    GL_ARRAY_BUFFER, GL_ELEMENT_ARRAY_BUFFER, GL_STATIC_DRAW, GL_FLOAT,
    GL_FALSE, GL_TRIANGLES, GL_UNSIGNED_INT, GL_TEXTURE_2D, GL_TEXTURE0,
    GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER, GL_LINEAR, GL_LINEAR_MIPMAP_LINEAR,
    GL_REPEAT, GL_RGB, GL_RGB8, GL_UNSIGNED_BYTE, GL_DEPTH_TEST, GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT, GL_VERTEX_SHADER, GL_FRAGMENT_SHADER,
    glGenBuffers, glBindBuffer, glBufferData, glEnableVertexAttribArray,
    glVertexAttribPointer, glDrawElements, glGenTextures, glBindTexture,
    glTexParameteri, glTexImage2D, glGenerateMipmap, glActiveTexture, glEnable,
    glClearColor, glClear, glViewport, glDisableVertexAttribArray, glDeleteBuffers,
    glDeleteTextures, glPolygonMode, GL_FRONT_AND_BACK, GL_FILL,
)

VERTEX_SHADER = """
#version 120
attribute vec3 position;
attribute vec3 normal;
attribute vec2 uv;
attribute vec3 tangent;
uniform mat4 mvp;
uniform mat4 model;
varying vec2 v_uv;
varying mat3 v_tbn;
varying vec3 v_world;
void main() {
    vec3 N = normalize(mat3(model) * normal);
    vec3 T = normalize(mat3(model) * tangent);
    T = normalize(T - dot(T, N) * N);
    vec3 B = normalize(cross(N, T));
    v_tbn = mat3(T, B, N);
    vec4 world = model * vec4(position, 1.0);
    v_world = world.xyz;
    v_uv = uv;
    gl_Position = mvp * vec4(position, 1.0);
}
"""

FRAGMENT_SHADER = """
#version 120
uniform sampler2D normal_map;
uniform vec3 light_position;
uniform float uv_scale;
uniform float normal_strength;
uniform float light_intensity;
varying vec2 v_uv;
varying mat3 v_tbn;
varying vec3 v_world;
void main() {
    vec3 sampled = texture2D(normal_map, v_uv * uv_scale).rgb * 2.0 - 1.0;
    sampled.xy *= normal_strength;
    vec3 N = normalize(v_tbn * normalize(sampled));
    vec3 L = normalize(light_position - v_world);
    vec3 V = normalize(vec3(0.0, 0.0, 5.0) - v_world);
    vec3 H = normalize(L + V);
    float diffuse = max(dot(N, L), 0.0);
    float specular = pow(max(dot(N, H), 0.0), 48.0) * 0.35;
    vec3 base = vec3(0.055, 0.36, 0.52);
    vec3 color = base * (0.18 + diffuse * light_intensity) + vec3(specular * light_intensity);
    gl_FragColor = vec4(color, 1.0);
}
"""


def _mesh_plane():
    p = [(-1,0,-1),(1,0,-1),(1,0,1),(-1,0,1)]
    n = [(0,1,0)]*4
    t = [(1,0,0)]*4
    uv = [(0,1),(1,1),(1,0),(0,0)]
    return _pack(p,n,uv,t,[0,2,1,0,3,2])


def _mesh_cube():
    positions=[]; normals=[]; uvs=[]; tangents=[]; indices=[]
    faces=[
      ((0,0,1),(1,0,0),(-1,-1,1)),((0,0,-1),(-1,0,0),(1,-1,-1)),
      ((1,0,0),(0,0,-1),(1,-1,1)),((-1,0,0),(0,0,1),(-1,-1,-1)),
      ((0,1,0),(1,0,0),(-1,1,1)),((0,-1,0),(1,0,0),(-1,-1,-1))
    ]
    for normal,tangent,origin in faces:
        bitangent=np.cross(normal,tangent)
        base=len(positions)
        for u,v in ((0,0),(1,0),(1,1),(0,1)):
            pos=np.array(origin,dtype=float)+np.array(tangent)*2*u+bitangent*2*v
            positions.append(tuple(pos)); normals.append(normal); tangents.append(tangent); uvs.append((u,v))
        indices.extend([base,base+1,base+2,base,base+2,base+3])
    return _pack(positions,normals,uvs,tangents,indices)


def _mesh_sphere(segments=48, rings=24):
    p=[]; n=[]; uv=[]; t=[]; idx=[]
    for y in range(rings+1):
        v=y/rings; phi=v*math.pi
        for x in range(segments+1):
            u=x/segments; theta=u*2*math.pi
            nx=math.sin(phi)*math.cos(theta); ny=math.cos(phi); nz=math.sin(phi)*math.sin(theta)
            p.append((nx,ny,nz)); n.append((nx,ny,nz)); uv.append((u,v))
            t.append((-math.sin(theta),0,math.cos(theta)))
    for y in range(rings):
        for x in range(segments):
            a=y*(segments+1)+x; b=a+segments+1
            idx.extend([a,b,a+1,a+1,b,b+1])
    return _pack(p,n,uv,t,idx)


def _mesh_cylinder(segments=48):
    p=[]; n=[]; uv=[]; t=[]; idx=[]
    for y in range(2):
        yy=-1.0+2.0*y
        for x in range(segments+1):
            u=x/segments; angle=u*2*math.pi
            nx=math.cos(angle); nz=math.sin(angle)
            p.append((nx,yy,nz)); n.append((nx,0,nz)); uv.append((u,float(y))); t.append((-nz,0,nx))
    for x in range(segments):
        a=x; b=x+segments+1
        idx.extend([a,b,a+1,a+1,b,b+1])
    # End caps with separate normals and UVs.
    for y,normal in ((-1,(0,-1,0)),(1,(0,1,0))):
        center=len(p); p.append((0,y,0)); n.append(normal); uv.append((.5,.5)); t.append((1,0,0))
        ring=len(p)
        for x in range(segments):
            angle=x/segments*2*math.pi
            p.append((math.cos(angle),y,math.sin(angle))); n.append(normal)
            uv.append((.5+.5*math.cos(angle),.5+.5*math.sin(angle))); t.append((1,0,0))
        for x in range(segments):
            a=ring+x; b=ring+(x+1)%segments
            idx.extend([center,a,b] if y<0 else [center,b,a])
    return _pack(p,n,uv,t,idx)


def _pack(positions,normals,uvs,tangents,indices):
    vertices=np.column_stack((positions,normals,uvs,tangents)).astype(np.float32)
    return vertices,np.asarray(indices,dtype=np.uint32)


class NormalMap3DPreview(QOpenGLWidget):
    """Interactive OpenGL normal-map material preview with four mesh primitives."""

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setMinimumSize(480,480)
        self.mesh_name="Plane"
        self.normal_image=None
        self.uv_scale=1.0
        self.normal_strength=1.0
        self.light_intensity=1.0
        self.rotation_x=28.0
        self.rotation_y=-28.0
        self._drag=None
        self._program=None
        self._buffers=[]
        self._texture=0
        self._meshes={}
        self._gl_error=""
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_normal_map(self,image):
        self.normal_image=None if image is None else np.ascontiguousarray(image[...,:3],dtype=np.uint8)
        if self.isValid():
            self.makeCurrent()
            self._upload_texture()
            self.doneCurrent()
        self.update()

    def set_mesh(self,name):
        if name in {"Plane","Cube","Sphere","Cylinder"}:
            self.mesh_name=name
            self.update()

    def set_uv_scale(self,value):
        self.uv_scale=float(value); self.update()

    def set_normal_strength(self,value):
        self.normal_strength=float(value); self.update()

    def set_light_intensity(self,value):
        self.light_intensity=float(value); self.update()

    def initializeGL(self):
        try:
            glEnable(GL_DEPTH_TEST)
            glClearColor(0.075,0.085,0.105,1.0)
            self._program=QOpenGLShaderProgram(self)
            if not self._program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex,VERTEX_SHADER):
                raise RuntimeError(self._program.log())
            if not self._program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment,FRAGMENT_SHADER):
                raise RuntimeError(self._program.log())
            for name,location in (("position",0),("normal",1),("uv",2),("tangent",3)):
                self._program.bindAttributeLocation(name,location)
            if not self._program.link():
                raise RuntimeError(self._program.log())
            self._meshes={"Plane":_mesh_plane(),"Cube":_mesh_cube(),
                          "Sphere":_mesh_sphere(),"Cylinder":_mesh_cylinder()}
            self._buffers=[int(glGenBuffers(1)),int(glGenBuffers(1))]
            self._texture=int(glGenTextures(1))
            self._upload_texture()
        except Exception as exc:
            self._gl_error=str(exc)

    def _upload_texture(self):
        if not self._texture:
            return
        image=self.normal_image
        if image is None:
            image=np.zeros((2,2,3),dtype=np.uint8); image[:]=[128,128,255]
        image=np.ascontiguousarray(np.flipud(image))
        h,w,_=image.shape
        glBindTexture(GL_TEXTURE_2D,self._texture)
        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D,0x2802,GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D,0x2803,GL_REPEAT)
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGB8,w,h,0,GL_RGB,GL_UNSIGNED_BYTE,image)
        glGenerateMipmap(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D,0)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        if self._gl_error:
            return
        if not self._program or not self._texture:
            return
        w=max(1,self.width()); h=max(1,self.height())
        glViewport(0,0,w,h)
        vertices,indices=self._meshes[self.mesh_name]
        glBindBuffer(GL_ARRAY_BUFFER,self._buffers[0])
        glBufferData(GL_ARRAY_BUFFER,vertices.nbytes,vertices,GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,self._buffers[1])
        glBufferData(GL_ELEMENT_ARRAY_BUFFER,indices.nbytes,indices,GL_STATIC_DRAW)

        projection=QMatrix4x4()
        projection.perspective(42.0,w/float(h),0.1,100.0)
        view=QMatrix4x4()
        view.lookAt(QVector3D(0,2.4,4.4),QVector3D(0,0,0),QVector3D(0,1,0))
        model=QMatrix4x4()
        model.rotate(self.rotation_x,1,0,0)
        model.rotate(self.rotation_y,0,1,0)
        if self.mesh_name=="Plane":
            model.scale(1.45,1.0,1.45)
        mvp=projection*view*model

        self._program.bind()
        self._program.setUniformValue("mvp",mvp)
        self._program.setUniformValue("model",model)
        self._program.setUniformValue("light_position",QVector3D(-2.5,4.0,3.0))
        self._program.setUniformValue("uv_scale",self.uv_scale)
        self._program.setUniformValue("normal_strength",self.normal_strength)
        self._program.setUniformValue("light_intensity",self.light_intensity)
        self._program.setUniformValue("normal_map",0)
        glActiveTexture(GL_TEXTURE0); glBindTexture(GL_TEXTURE_2D,self._texture)
        stride=11*4
        for location,size,offset in ((0,3,0),(1,3,12),(2,2,24),(3,3,32)):
            glEnableVertexAttribArray(location)
            glVertexAttribPointer(location,size,GL_FLOAT,GL_FALSE,stride,ctypes.c_void_p(offset))
        glDrawElements(GL_TRIANGLES,len(indices),GL_UNSIGNED_INT,None)
        for location in (0,1,2,3):
            glDisableVertexAttribArray(location)
        glBindTexture(GL_TEXTURE_2D,0)
        self._program.release()
        glBindBuffer(GL_ARRAY_BUFFER,0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,0)

    def paintEvent(self,event):
        if self._gl_error:
            from PySide6.QtGui import QPainter, QColor
            painter=QPainter(self); painter.fillRect(self.rect(),QColor("#15181d"))
            painter.setPen(QColor("#ff9b8f"))
            painter.drawText(self.rect().adjusted(20,20,-20,-20),
                Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,
                "3D preview could not initialize OpenGL:\n"+self._gl_error)
            painter.end()
            return
        super().paintEvent(event)

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            self._drag=event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept(); return
        super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        if self._drag is not None:
            p=event.position(); delta=p-self._drag; self._drag=p
            self.rotation_y+=delta.x()*0.6
            self.rotation_x=max(-89.0,min(89.0,self.rotation_x+delta.y()*0.6))
            self.update(); event.accept(); return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            self._drag=None; self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept(); return
        super().mouseReleaseEvent(event)

    def closeEvent(self,event):
        if self.isValid():
            self.makeCurrent()
            for buffer in self._buffers:
                if buffer: glDeleteBuffers(1,[buffer])
            if self._texture: glDeleteTextures(1,[self._texture])
            self.doneCurrent()
        super().closeEvent(event)
