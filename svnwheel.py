import sys
import pyglet
from pyglet.gl import *
import math
from xml.etree.ElementTree import ElementTree

"""
Subversion visualisation

TODO: Handle directory copies
"""

data = dict()
maxRev = 0
window = pyglet.window.Window(resizable=True)

label = pyglet.text.Label(font_name='Arial',
                          font_size=12,
                          x=window.width//2, y=14,
                          anchor_x='center', anchor_y='center')

def setup():
   glClearColor(0.15, 0.15, 0.15, 1)
   glColor3f(1, 0, 0)
   glDisable(GL_DEPTH_TEST)
   glDisable(GL_CULL_FACE)
   glDisable(GL_LIGHTING)
    
@window.event
def on_resize(width, height):
   glViewport(0, 0, width, height)
   glMatrixMode(GL_PROJECTION)
   glLoadIdentity()
   glOrtho(0, width, 0, height, -1, 100)
   glMatrixMode(GL_MODELVIEW)
   
   label.x = window.width // 2
   
   return pyglet.event.EVENT_HANDLED

@window.event
def on_draw():
    window.clear()
    render_data(window, data)
    glLoadIdentity()
    label.draw()
    
@window.event
def on_mouse_motion(x, y, dx, dy):
    select_data(x, y)
            
def get_data(filename):
    tree = ElementTree()
    xmlRoot = tree.parse(filename)
    maxRev = 0
    
    print('Fetching data')
    print('Found {0} entries'.format(len(xmlRoot.findall('logentry'))))
    
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
                print('found path copy {0} {1}'.format(pathElement.attrib['copyfrom-path'], pathElement.text))
                for key in data.keys():
                    lastDataEntry = data[key][len(data[key]) - 1];
                    print('{0} {1} {2}'.format(key, (int(logElement.attrib['revision'])), lastDataEntry))
                    if key.startswith(pathElement.attrib['copyfrom-path']) and (lastDataEntry[0] == (int(logElement.attrib['revision'])) or lastDataEntry[1] != 'D'):
                        newKey = key.replace(pathElement.attrib['copyfrom-path'], pathElement.text)
                        data[newKey] = []
                        print('{0} {1}'.format(newKey, pathElement.text))
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
    maxRadius = min(centreX - 30, centreY - 30)
    revStep = float(maxRadius) / maxRev
    
    glMatrixMode(GL_MODELVIEW)    
    glLoadIdentity()
    glTranslatef(float(centreX), float(centreY), 0.0)
	
    currentAngle = 0.0
    itemIndex = 0
    for key in sorted(data.iterkeys()):
        item = data[key]
        glLoadName(GLuint(itemIndex))
        for i in range(0, len(item) - 1):
            j = float(item[i + 1][0]) / maxRev
            r, g, b = hsv_to_rgb(currentAngle, j, 1.0)
            glColor3f(r, g, b)
            gluPartialDisk(quadric, item[i][0] * revStep, item[i + 1][0] * revStep, 6, 1, currentAngle, angleStep)
        
        if item[len(item) - 1][1] != 'D':
            r, g, b = hsv_to_rgb(currentAngle, 1.0, 1.0)
            glColor3f(r, g, b)
            gluPartialDisk(quadric, item[len(item) - 1][0] * revStep, maxRadius, 6, 1, currentAngle, angleStep)            
        
        # Render points on commits
        glColor3f(1, 1, 1)
        for i in range(len(item)):
            # Calculate point radius
            pointRadius = math.tan((math.radians(angleStep / 2)) * 0.75) * (item[i][0] * revStep)
            glPushMatrix()
            glRotatef(currentAngle + (angleStep / 2), 0, 0, -1)
            glTranslatef(0, item[i][0] * revStep, 0)
            gluDisk(quadric, 0, pointRadius, 12, 1)
            glPopMatrix()
            
        currentAngle = currentAngle + angleStep
        itemIndex = itemIndex + 1

def select_data(x, y):
    buffer = (GLuint * 8)(0)
    glSelectBuffer(8, buffer)

    view = (GLint * 4)(0)
    glGetIntegerv(GL_VIEWPORT, view)
    
    hits = 0
    
    glRenderMode(GL_SELECT)
    
    glInitNames()
    glPushName(0)
    
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluPickMatrix(x, y, 1, 1, view)
    glOrtho(0, window.width, 0, window.height, -1, 100)

    glMatrixMode(GL_MODELVIEW)
    render_data(window, data)
    
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()

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
pyglet.app.run()
