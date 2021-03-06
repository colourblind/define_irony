import sys
import math
from xml.etree.ElementTree import ElementTree
import pyglet
from pyglet.gl import *

"""
Subversion visualisation
"""

data = dict()
maxRev = 0
window = pyglet.window.Window(resizable=True)
fps = pyglet.clock.ClockDisplay()
showFps = False
displayList = 0
x = 0
y = 0
z = 280

label = pyglet.text.Label(font_name='Arial',
                          font_size=12,
                          color=(255, 255, 255, 255),
                          x=window.width//2, y=14,
                          anchor_x='center', anchor_y='center')
shadow = pyglet.text.Label(font_name='Arial',
                          font_size=12,
                          color=(0, 0, 0, 255),
                          x=window.width//2 + 1, y=14 - 1,
                          anchor_x='center', anchor_y='center')
      

def setup():
    glClearColor(0.15, 0.15, 0.15, 1)
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_CULL_FACE)
    glDisable(GL_LIGHTING)
    
@window.event
def on_resize(width, height):
    glViewport(0, 0, width, height)
    label.x = window.width // 2
    return pyglet.event.EVENT_HANDLED

@window.event
def on_draw():
    window.clear()
    set_camera()
    glCallList(displayList)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, window.width, 0, window.height, -1, 100)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    shadow.text = label.text
    shadow.x = label.x + 1
    shadow.draw()
    label.draw()
    if showFps:
        fps.draw()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    
@window.event
def on_mouse_motion(mx, my, dx, dy):
    select_data(mx, my)

@window.event
def on_mouse_drag(mx, my, dx, dy, button, modifiers):
    global x, y, z
    label.text = ''
    if button == pyglet.window.mouse.LEFT:
        x += dx
        y += dy
    if button == pyglet.window.mouse.RIGHT:
        z -= dy

@window.event
def on_mouse_release(mx, my, button, modifiers):
    select_data(mx, my)
        
@window.event
def on_key_press(symbol, modifiers):
    global x, y, z
    if symbol == pyglet.window.key.R:
        x = 0
        y = 0
        z = 280
        label.text = ''

def set_camera(picking=False, px=0, py=0, view=(GLint * 4)(0)):
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    if picking:
        gluPickMatrix(px, py, 1, 1, view)
    gluPerspective(90, float(window.width) / window.height, 0.5, 500);

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(x, y, z, x, y, z - 1, 0, 1, 0);
        
def get_data(filename):
    tree = ElementTree()
    xmlRoot = tree.parse(filename)
    maxRev = 0
    
    print('Fetching data')
    print('Found {0} entries'.format(len(xmlRoot.findall('logentry'))))
    
    data['/'] = []
    data['/'].append((0, 'A'));
    
    for logElement in reversed(xmlRoot.findall('logentry')):
        for pathElement in logElement.findall('paths/path'):
            # If a directory is deleted, remove all the files in it, but only if they've
            # not already been deleted
            if pathElement.attrib['action'] == 'D' and pathElement.attrib['kind'] == 'dir':
                for key in data.keys():
                    if key.startswith(pathElement.text) and data[key][len(data[key]) - 1][1] != 'D':
                        data[key].append((int(logElement.attrib['revision']), pathElement.attrib['action']))
            # Handle file and directory copies
            elif pathElement.attrib['action'] == 'A' and pathElement.attrib['kind'] == 'dir' and 'copyfrom-path' in pathElement.attrib:
                for key in data.keys():
                    lastDataEntry = data[key][len(data[key]) - 1];
                    if key.startswith(pathElement.attrib['copyfrom-path']) and (lastDataEntry[0] == (int(logElement.attrib['revision'])) or lastDataEntry[1] != 'D'):
                        newKey = key.replace(pathElement.attrib['copyfrom-path'], pathElement.text)
                        data[newKey] = []
                        data[newKey].append((int(logElement.attrib['revision']), pathElement.attrib['action']))
            else:
                if pathElement.text not in data:
                    data[pathElement.text] = []
                
                data[pathElement.text].append((int(logElement.attrib['revision']), pathElement.attrib['action']))
                maxRev = max(maxRev, int(logElement.attrib['revision']))
    
    return data, maxRev
    
def render_data(window, data):
    centreX = window.width // 2
    centreY = window.height // 2 + 10
    quadric = gluNewQuadric()    
    angleStep = 360.0 / len(data)
    maxRadius = 250
    revStep = float(maxRadius) / maxRev
    	
    currentAngle = 0.0
    itemIndex = 0
    
    displayList = glGenLists(1)
    glNewList(displayList, GL_COMPILE)
    
    for key in sorted(data.iterkeys()):
        item = data[key]
        glLoadName(GLuint(itemIndex))
        for i in range(0, len(item) - 1):
            j = float(item[i + 1][0]) / maxRev
            r, g, b = hsv_to_rgb(currentAngle, j, 1.0)
            glColor3f(r, g, b)
            gluPartialDisk(quadric, item[i][0] * revStep, item[i + 1][0] * revStep, 2, 1, currentAngle, angleStep)
        
        if item[len(item) - 1][1] != 'D':
            r, g, b = hsv_to_rgb(currentAngle, 1.0, 1.0)
            glColor3f(r, g, b)
            gluPartialDisk(quadric, item[len(item) - 1][0] * revStep, maxRadius, 2, 1, currentAngle, angleStep)            
        
        # Render points on commits
        glColor3f(1, 1, 1)
        for i in range(len(item)):
            # Calculate point radius
            pointRadius = math.tan((math.radians(angleStep / 2)) * 0.75) * (item[i][0] * revStep)
            glPushMatrix()
            glRotatef(currentAngle + (angleStep / 2), 0, 0, -1)
            glTranslatef(0, item[i][0] * revStep, 0)
            gluDisk(quadric, 0, pointRadius, 10, 1)
            glPopMatrix()
            
        currentAngle = currentAngle + angleStep
        itemIndex = itemIndex + 1
    glEndList()
    
    return displayList

def select_data(x, y):
    buffer = (GLuint * 8)(0)
    glSelectBuffer(8, buffer)

    view = (GLint * 4)(0)
    glGetIntegerv(GL_VIEWPORT, view)
    
    hits = 0
        
    glRenderMode(GL_SELECT)
    
    glInitNames()
    glPushName(0)

    set_camera(True, x, y, view)
    glCallList(displayList)

    hits = glRenderMode(GL_RENDER)

    label.text = ''
    for i in range(hits):
        label.text = sorted(data.keys())[buffer[3]]
    
def hsv_to_rgb(h, s, v):
    if s == 0:
        return v, v, v
    
    h /= 60
    i = math.floor(h)
    f = h - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    
    if i == 0:
        r = v; g = t; b = p
    elif i == 1:
        r = q; g = v; b = p
    elif i == 2:
        r = p; g = v; b = t
    elif i == 3:
        r = p; g = q; b = v
    elif i == 4:
        r = t; g = p; b = v
    else:
        r = v; g = p; b = q
    
    if r > 1:
        raise ValueError('r over ' + str(r))
    if g > 1:
        raise ValueError('g over ' + str(g))    
    if b > 1:
        raise ValueError('b over ' + str(b))

    return r, g, b
    
setup()
filename = 'log.xml'
if len(sys.argv) > 1:
    filename = sys.argv[1]
data, maxRev = get_data(filename)
displayList = render_data(window, data)
pyglet.app.run()
