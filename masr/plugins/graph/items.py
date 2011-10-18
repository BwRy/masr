# -*- coding: utf-8 -*-
# Copyright (C) 2009 Axel Tillequin (bdcht3@gmail.com) 
# This code is part of Masr
# published under GPLv2 license


import gtk
import math
from numpy import array

from goocanvas import *

# connectors CX are embedded inside node views. These objects are drawn on
# the node's surface and exists only as sub-objects of their node. CX are used
# as 'ports' for edges connected with a node. A node can have several such CX
# and can register or unregister its edges on such CX.
class CX(Rect):
    def __init__(self,e=None):
        Rect.__init__(self,width=3,height=3)
        self.set_properties(line_width=0,fill_color='red')
        #self.props.visibility=False
        # list of edges connected to this CX:
        self.registered = []
        if e!=None: self.register(e)
        #self.connect('event',CX.eventhandler)

    def set_wh(self,wh):
        self.set_properties(width = wh[0], height = wh[1])
    def get_wh(self):
        return self.get_properties('width','height')
    wh = property(get_wh,set_wh)

    def getpos(self):
        bb = self.get_bounds()
        return (bb.x1,bb.y1)

    # manage Edge_basic that are using this CX:
    def register(self,item):
        self.registered.append(item)
    def unregister(self,item):
        self.registered.remove(item)

    def eventhandler(*args):
        print "CX eventhandler on",args

#------------------------------------------------------------------------------
# decorators for eventhandlers: this sets the 'clicked' field to the mouse
# button id, and moves the object along with mouse-1 movements.
def mouse1moves(h):
    def wrapper(self,item,e):
        #self.last_msec = [0]
        if e.type is gtk.gdk.BUTTON_PRESS:
            self.clicked = e.button
            self.oldx,self.oldy = e.get_coords()
            #self.last_msec[0] = 0.
        elif e.type is gtk.gdk.BUTTON_RELEASE:
            self.clicked = 0
        elif e.type is gtk.gdk.MOTION_NOTIFY:
            #if abs(e.time - self.last_msec[0])<10: return False
            #self.last_msec[0]=e.time
            if self.clicked==1:
                newx,newy = e.get_coords()
                tx,ty = newx-self.oldx,newy-self.oldy
                self.translate(tx,ty)
                self.notify('transform')
        return h(self,item,e)
    return wrapper

#------------------------------------------------------------------------------
# This is a 'circle' shaped view for nodes. 
class Node_basic(Group):
    #prop:
    def set_r(self,r):
        self._r = r
        self.el.set_properties(radius_x = r, radius_y = r)
    def get_r(self):
        return self._r
    r = property(get_r,set_r)

    def set_wh(self,wh): pass
    def get_wh(self):
        bb = self.get_bounds()
        return (bb.x2-bb.x1,bb.y2-bb.y1)
    wh = property(get_wh,set_wh)

    # put the cx pt at the intersection between the circle shape of Node_basic
    # and the radius from centre to pt 'topt'. 
    def intersect(self,topt,cx):
        assert self.find_child(cx)!=-1
        #get cx pos on canvas:
        r = self.get_canvas()
        x1,y1 = self.props.x,self.props.y
        x1,y1 = r.convert_from_item_space(self,x1,y1)
        # intersect with target pt:
        x2,y2 = topt
        theta = math.atan2(y2-y1,x2-x1)
        newx = int(math.cos(theta)*self._r)
        newy = int(math.sin(theta)*self._r)
        cx.set_properties(x=newx,y=newy)
        self._angle = theta

    def set_alpha(self,a):
        color = self.props.fill_color_rgba & 0xffffff00
        self.props.fill_color_rgba = color+(int(a*255.)&0xff)
    def get_alpha(self):
        return (self.props.fill_color_rgba&0xff)/255.
    alpha = property(get_alpha,set_alpha)

    def __init__(self,r=10):
        Group.__init__(self)
        self.el = Ellipse(parent=self,
                          fill_color='gray88',
                          stroke_color='black',
                          line_width=2)
        # extra:
        self.alpha = 1.
        self.r = r
        self.label = Text(parent=self,
                          text='[?]',
                          font="monospace, bold, 8",
                          fill_color='blue',
                          anchor=gtk.ANCHOR_CENTER)
        #self.label.props.visibility = False
        # edges connectors:
        self.cx = []
        # events:
        self.connect("enter-notify-event",Node_basic.eventhandler)
        self.connect("leave-notify-event",Node_basic.eventhandler)
        self.connect("button-press-event",Node_basic.eventhandler)
        self.connect("button-release-event",Node_basic.eventhandler)
        self.connect("motion-notify-event",Node_basic.eventhandler)
        # clicked: 1=mouse1, 2=mouse2, 3=mouse3
        self.clicked=0
        self.connect('notify::transform',Node_basic.notifyhandler)

    @mouse1moves
    def eventhandler(self,item,e):
        if e.type is gtk.gdk.ENTER_NOTIFY:
            self.props.line_width=2.0
        elif e.type is gtk.gdk.LEAVE_NOTIFY:
            self.props.line_width=1.0
        return False

    def notifyhandler(self,prop):
        #print "notify %s on "%prop.name,self
        for cx in self.cx:
            for e in cx.registered: e.update_points()

#------------------------------------------------------------------------------
class Edge_basic(Polyline):
    def __init__(self,n0,n1,head=False):
        self.n = [n0,n1]
        x0,y0 = n0.props.x,n0.props.y
        x1,y1 = n1.props.x,n1.props.y
        self.cx = [CX(self),CX(self)]
        n0.cx.append(self.cx[0]); n0.add_child(self.cx[0])
        n1.cx.append(self.cx[1]); n1.add_child(self.cx[1])
        Polyline.__init__(self,points=Points([(x0,y0),(x1,y1)]))
        self.set_properties(close_path=False,
                            stroke_color='black',
                            end_arrow=True,
                            line_width=2)
        if head:
            self.set_properties(end_arrow=True)
        self.update_points()
        self.clicked=0

    def setpath(self,l):
        self.props.points = Points(l)

    def update_points(self):
        pts = self.props.points.coords
        self.n[0].intersect(topt=pts[1],cx=self.cx[0])
        self.n[1].intersect(topt=pts[-2],cx=self.cx[-1])
        self.cx[-1].props.fill_color='blue'
        cx = self.cx[0].getpos()
        pts[0] = cx
        cx = self.cx[-1].getpos()
        pts[-1] =  cx
        self.props.points = Points(pts)

#------------------------------------------------------------------------------
class Edge_curve(Path):

    def __init__(self,n0,n1,head=True):
        self.n = [n0,n1]
        self.has_head=head
        self.cx = [CX(self),CX(self)]
        n0.cx.append(self.cx[0]); n0.add_child(self.cx[0])
        n1.cx.append(self.cx[1]); n1.add_child(self.cx[1])
        Path.__init__(self)
        self.props.stroke_color = 'black'
        self.props.line_width = 1
        self.props.line_cap = 1
        self.props.line_join = 1
        self.splines = [[(n0.props.x,n0.props.y),(n1.props.x,n1.props.y)]]
        self.update_points()
        self.clicked=0

    def write_data(self):
        p0 = self.splines[0][0]
        data = "M %d %d"%p0
        for s in self.splines:
            if len(s)==2:
                data += " L %d %d"%s[1]
            else:
                data += " C %d %d"%s[1]
                data += " %d %d"%s[2]+" %d %d"%s[3]
        if self.has_head:
            pass
        self.props.data = data

    def setpath(self,l):
        try:
            self.splines = self.setcurve(l)
        except:
            pass

    def update_points(self):
        try:
            spl0 = self.splines[0]
            spl1 = self.splines[-1]
            self.n[0].intersect(topt=spl0[1],cx=self.cx[0])
            self.n[1].intersect(topt=spl1[-2],cx=self.cx[1])
            cx = (self.cx[0].props.x,self.cx[0].props.y)
            spl0[0] = cx
            cx = (self.cx[1].props.x,self.cx[1].props.y)
            spl1[-1] = cx
            self.write_data()
        except:
            pass

#------------------------------------------------------------------------------
class Node_codeblock(Group):

    def __init__(self,code):
        Group.__init__(self)
        self.codebox = Rect(parent=self,can_focus=True)
        self.code = Text(parent=self,
                         text=code,
                         font='monospace, 10',
                         use_markup=True,
                         fill_color='black')
        self.padding = 4
        bbink,bblogic = self.code.get_natural_extents()
        w  = (bblogic[2]*0.001)+2*self.padding
        h  = (bblogic[3]*0.001)+2*self.padding
        self.codebox.set_properties(width=w,height=h)
        self.codebox.set_properties(fill_color='white',
                                    stroke_color='black',
                                    line_width=1)
        self.code.raise_(self.codebox)
        # shadow :
        self.shadow = s = 2
        self.codebox.set_properties(x=-s,y=-s)
        self.code.set_properties(x=-s+self.padding,y=-s+self.padding)
        self.shadbox = Rect(x=s,y=s,width=w,height=h,
                            fill_color='grey44',
                            line_width=0)
        self._wh = (w+s+s,h+s+s)
        self.cx = []
        self.add_child(self.shadbox,0)
        self.shadbox.lower(self.codebox)
        # events:
        self.clicked=0
        self.connect("enter-notify-event",Node_codeblock.eventhandler)
        self.connect("leave-notify-event",Node_codeblock.eventhandler)
        self.connect("button-press-event",Node_codeblock.eventhandler)
        self.connect("button-release-event",Node_codeblock.eventhandler)
        self.connect("motion-notify-event",Node_codeblock.eventhandler)
        self.connect('notify::transform',Node_codeblock.notifyhandler)

    def set_wh(self,wh): pass
    def get_wh(self):
        return self._wh
    wh = property(get_wh,set_wh)

    def intersect(self,topt,cx):
        assert self.find_child(cx)!=-1
        bb = self.get_bounds()
        w,h = self.codebox.get_properties('width','height')
        x1,y1 = w/2,h/2
        x2,y2 = topt[0]-bb.x1,topt[1]-bb.y1
        # now try all 4 segments of self rectangle:
        S = [((x1,y1),(x2,y2),(0,0),(w,0)),
             ((x1,y1),(x2,y2),(w,0),(w,h)),
             ((x1,y1),(x2,y2),(0,h),(w,h)),
             ((x1,y1),(x2,y2),(0,h),(0,0))]
        for segs in S:
            xy = intersect2lines(*segs)
            if xy!=None:
                cx.set_properties(x=xy[0]-self.shadow,y=xy[1]-self.shadow)
                break

    def highlight_on(self,style=None):
        import re
        if style is None:
            style = {'addr': '<span foreground="blue">%s</span>',
                     'code': '<span foreground="black">%s</span>',
                     'mnem': '<span foreground="black" weight="bold">%s</span>',
                     'strg': '<span foreground="DarkRed">%s</span>',
                     'cons': '<span foreground="red">%s</span>',
                     'comm': '<span foreground="DarkGreen">%s</span>',
                    }
        lre = re.compile("(0x[0-9a-f]+ )('[0-9a-f]+' +)(.*)$")
        hcode = []
        for l in self.code.get_properties('text').splitlines():
            if l.startswith('#'):
                hcode.append(style['comm']%l)
            else:
                m = lre.match(l)
                if m is None: return
                g = m.groups()
                s  = [style['addr']%g[0]]
                s += [style['strg']%g[1]]
                s += [style['code']%g[2]]
                hcode.append(''.join(s))
        self.code.set_properties(text='\n'.join(hcode))
        self.code.set_properties(use_markup=True)

    def highlight_off(self):
        import re
        lre = re.compile("<span [^>]+>(.*?)</span>")
        code = []
        for l in self.code.get_properties('text').splitlines():
            g = lre.findall(l)
            if len(g)>0: code.append(''.join(g))
        self.code.set_properties(text='\n'.join(code))
        self.code.set_properties(use_markup=False)

    @mouse1moves
    def eventhandler(self,item,e):
        if e.type is gtk.gdk.ENTER_NOTIFY:
            self.codebox.set_properties(line_width=2.0)
        elif e.type is gtk.gdk.LEAVE_NOTIFY:
            self.codebox.set_properties(line_width=1.0)
        return False

    def notifyhandler(self,prop):
        #print "notify %s on "%prop.name,self
        for cx in self.cx:
            for e in cx.registered: e.update_points()

    def resrc(self,code):
        self.code.props.text = code
        bb = self.code.get_bounds()
        w  = (bb.x2-bb.x1)+self.padding
        h  = (bb.y2-bb.y1)+self.padding
        self.codebox.set_properties(width=w,height=h)
        self.shadbox.set_properties(width=w,height=h)


def intersect2lines((x1,y1),(x2,y2),(x3,y3),(x4,y4)):
    b = (x2-x1,y2-y1)
    d = (x4-x3,y4-y3)
    det = b[0]*d[1] - b[1]*d[0]
    if det==0: return None
    c = (x3-x1,y3-y1)
    t = float(c[0]*b[1] - c[1]*b[0])/(det*1.)
    if (t<0. or t>1.): return None
    t = float(c[0]*d[1] - c[1]*d[0])/(det*1.)
    if (t<0. or t>1.): return None
    x = x1 + t*b[0]
    y = y1 + t*b[1]
    return (x,y)
