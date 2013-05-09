#coding:utf8
import os
import MySQLdb
import json
outGimp = None
screenWidth = 960
screenHeight = 640
#NGUI
def gimpToUnity(x, y):
    x -= screenWidth/2
    y = screenHeight-y+-screenHeight/2
    return x, y

def findL(p, n):
    for i in p:
        if i.name == n:
            return i
        #group
        if hasattr(i, 'layers'):
            ret = findL(i.layers, n)
            if ret != None:
                return ret
        elif i.name == n:
            return i
    return None


def getRel(l, n0, n1):
    n0 = findL(l, n0)
    n1 = findL(l, n1)
    o0 = n0.offsets
    o1 = n1.offsets
    print o1[0]-o0[0], o1[1]-o0[1], n1.width, n1.height

def getRelLayer(n0, n1):
    o0 = n0.offsets
    o1 = n1.offsets
    print o1[0]-o0[0], o1[1]-o0[1], n1.width, n1.height

def getAllChilds(layer):
    ret = []
    for i in layer:
        if hasattr(i, 'layers'):
            ret += getAllChilds(i.layers)
        else:
            ret.append(i)
    return ret
#生成所有图层的位置和大小
def genLayerPosAndScale(p, back, pdb=None):
    b = findL(p.layers, back)
    #l = list(p.layers)
    l = getAllChilds(p.layers)
    res = []
    
    for i in l:
        if i.visible and i != b:
            sca = i.width/64.0
            px = i.offsets[0]-b.offsets[0]+i.width/2
            py = 640-(i.offsets[1]-b.offsets[1]+i.height/2)
            res.append([px, py, sca])
    print 'float pos[] = {'
    for i in res:
        print i[0],',', i[1],',',i[2],","
    print '};'
    print 'int len = ', len(res)*3,';'
    return res

#gimpOutput 文件夹中生成代码
def genJsonFile(l, back, curPic, pdb, strings):
    for i in l:
        if i.visible:
            if hasattr(i, 'layers'):
                nl = i.layers
                l.reverse()
                genJsonFile(l, back, curPic, pdb, strings)
            else:
                px = i.offsets[0] - back.offsets[0]
                py = i.offsets[1] - back.offsets[1]

                px -= 512
                py = 768-py+-384


#NGUI 需要的 C# 代码
def genCSharpCode(l, back, curPic, pdb, strings, depth):
    ret = ""
    callbacks = []
    for i in l:
        if i.visible:
            if hasattr(i, 'layers'):
                iName = i.name.replace('＃', '#')
                attris = iName.split('#')
                isPanel = False
                for a in attris[1:]:
                    if a == 'item':
                        isPanel = True
                        break

                nl = i.layers
                nl.reverse()
                #不支持多层嵌套拖动view
                if isPanel:
                    ret += "\t\tpanel2 = NGUITools.AddChild<UIPanel>(anchor.gameObject);\n"
                    ret += "\t\tdrag = panel2.gameObject.AddComponent<UIDraggablePanel>();\n"
                    ret += "\t\tpanel2.clipping = UIDrawCall.Clipping.SoftClip;\n"
                    pwid = i.width
                    phei = i.height
                    x, y = i.offsets
                    x, y = gimpToUnity(x, y)
                    ret += "\t\tpanel2.clipRange = new Vector4(%d, %d, %d, %d);\n" % (x+pwid/2, y-phei/2, pwid, phei)
                    ret += "\t\tpanel2.clipSoftness = new Vector2(10, 10);\n"
                    ret += "\t\tdrag.scale = new Vector3(0, 1, 0);\n"
                    ret += "\t\toldObject = rootObject;\n"
                    ret += "\t\trootObject = panel2.gameObject;\n"

                newRet, depth, newCallback = genCSharpCode(nl, back, curPic, pdb, strings, depth)
                ret += newRet
                callbacks += newCallback
                if isPanel:
                    ret += "\t\trootObject = oldObject;\n"
            else:
                iName = i.name.replace('＃', '#')
                attris = iName.split('#')   
                name = attris[0]
                if name[-1] == ' ':
                    name = name[:-1]
                #使用数据库中的字符
                name = curPic.get(name, name)
                """
                TopLeft,
                Top,
                TopRight,
                Left,
                Center,
                Right,
                BottomLeft,
                Bottom,
                BottomRight,
                """
                pivot = "TopLeft"
                mx = 0
                my = 0
                button = False
                callback = None


                for a in attris[1:]:
                    if a[-1] == ' ':
                        a = a[:-1]
                    if a == 'left':
                        mx = 0
                    if a == 'top':
                        my = 0
                    if a == 'mx':
                        mx = 1
                    if a == 'my':
                        my = 1
                    if a == 'mid':
                        mx = 1
                        my = 1
                    if a == 'right':
                        mx = 2
                    if a == 'bottom':
                        my = 2
                    if a == 'b':
                        button = True
                        mx = 1
                        my = 1
                        #callback = "On%s" % (name.capitalize())
                    if a[0] == 'c':
                        callback = a[1:]
                        callbacks.append(callback)

                pi = my*10+mx
                if pi == 0:
                    pivot = "TopLeft"
                elif pi == 1:
                    pivot = "Top"
                elif pi == 2:
                    pivot = "Right"
                elif pi == 10:
                    pivot = "Left"
                elif pi == 11:
                    pivot = "Center"
                elif pi == 12:
                    pivot = "Right"
                elif pi == 20:
                    pivot = "BottomLeft"
                elif pi == 21:
                    pivot = "Bottom"
                elif pi == 22:
                    pivot = "BottomRight"

                wid = i.width
                hei = i.height

                #print "error", i.name, back.name
                px = i.offsets[0] - back.offsets[0]
                py = i.offsets[1] - back.offsets[1]


                px -= screenWidth/2
                py = screenHeight-py+-screenHeight/2
                

                px += wid*mx*50/100
                #unity3d 坐标是 左下角 0  0
                #gimp 坐标是 左上角 0 0
                py -= hei*my*50/100

                if button:
                    ret += "\t\tgo = NGUITools.AddChild(panel.gameObject);\n"
                    ret += "\t\tgo.name = \"Button(%s)\";\n" % (name)
                    ret += "\t\tgo.transform.localPosition = new Vector3(%df, %df, 0f);\n" % (px, py)
                    ret += "\n"
                    ret += "\t\tbg = NGUITools.AddChild<UISlicedSprite>(go);\n"
                    ret += "\t\tbg.name = \"Background\";\n"
                    ret += "\t\tbg.depth = %d;\n" % (depth)
                    ret += "\t\tbg.atlas = atlas;\n"
                    ret += "\t\tbg.spriteName = \"%s\";\n" % (name)
                    ret += "\t\tbg.transform.localScale = new Vector3(%df, %df, 1f);\n" % (wid, hei)

                    ret += "\t\tbg.MakePixelPerfect();\n"
                    ret += "\n"
                    #字体之后做
                    """
                    ret += "UILabel lbl = NGUITools.AddWidget<UILabel>(go);\n"
                    ret += "lbl.font = font;\n"
                    ret += "lbl.text = go.name;\n"
                    ret += "lbl.MakePixelPerfect();\n"
                    """
                    ret += "\n"
                    ret += "\t\tNGUITools.AddWidgetCollider(go);\n"
                    ret += "\n"
                    ret += "\t\tgo.AddComponent<UIButton>().tweenTarget = bg.gameObject;\n"
                    ret += "\t\tgo.AddComponent<UIButtonScale>();\n"
                    ret += "\t\tgo.AddComponent<UIButtonOffset>();\n"
                    ret += "\t\tgo.AddComponent<UIButtonSound>();\n"
                    if callback != None:
                        ret += "\t\tmessage = go.AddComponent<UIButtonMessage>();\n"
                        ret += "\t\tmessage.target = gameObject;\n"
                        ret += "\t\tmessage.trigger = UIButtonMessage.Trigger.OnRelease;\n"
                        ret += "\t\tmessage.functionName = \"%s\";\n" % (callback)


                    ret += "\n"
                else:
                    ret += "\t\tsprite = NGUITools.AddChild<UISprite>(panel.gameObject);\n"
                    ret += "\t\tsprite.name = sprite.name + \"(\" + \"%s\" + \")\";\n" % (name)
                    ret += "\t\tsprite.atlas = atlas;\n"
                    ret += "\t\tsprite.spriteName = \"%s\";\n" % (name)
                    ret += "\t\tsprite.pivot = UIWidget.Pivot.%s;\n" % (pivot)
                    ret += "\t\tsprite.MakePixelPerfect();\n"
                    ret += "\t\tsprite.transform.localPosition = new Vector3(%d, %d, 0);\n" % (px, py)
                    ret += "\t\tsprite.transform.localScale = new Vector3(%d, %d, 0);\n" % (wid, hei)
                    ret += "\t\tsprite.depth = %d;\n" % (depth)
                    ret += "\n";

                depth += 1
    return ret, depth, callbacks

            

#根据图层组结构生成代码
#相对的基础层 其他层
#类型 #l #s  label sprite
#最底图层back

#参数1 图层组 背景图层fir fL fTemp sca 值需要返回
#var but0;
#var line;
#var temp;
#var sca;

#unity3d 坐标系 中心是 0 0 相机坐标
def genLayerCode(l, back, curPic, pdb, strings):
    for i in l:
        #可见性决定是否生成代码
        if i.visible:
            if hasattr(i, 'layers'):
                l = i.layers
                l.reverse()
                genLayerCode(l, back, curPic, pdb, strings)
            else:
                iName = i.name.replace('＃', '#')
                attris = iName.split('#')   
                name = attris[0]
                if name[-1] == ' ':
                    name = name[:-1]
                #label = attris[1]
                label = 's'
                mx = 0
                my = None
                butWord = ""
                callBack = ""
                color = [100, 100, 100, 100]
                size = None
                lineH = 20
                alpha = 100

                itemNum = 3
                rowNum = 2
                direct = 'y'
                WIDTH = 100
                HEIGHT = 100
                OFFX = 100
                OFFY = 100
                export = False
                zord = 0
                sca = None
                labelMx = False
                #num_channels, pixel = pdb.gimp_drawable_get_pixel(i, 0, 0)#图层透明度
                #color[3] = pixel[3]*100/255
                altasColor = "white"

                for a in attris[1:]:
                    if a[-1] == ' ':
                        a = a[:-1]
                    if a == 'mx':
                        mx = 50
                    if a == 'my':
                        my = 50
                    if a == 'l':
                        label = a
                    if a == 's':
                        label = a
                    if a == 'b':
                        mx = 50
                        my = 50
                        label = 'b'
                    if a == 'mid':
                        mx = 50
                        my = 50
                    if a[0] == 'w':#按钮文字
                        butWord = a[1:]
                    if a[0] == 'c':#callback
                        callBack = a[1:]
                    if a[0] == 'r' and len(a[1:])  == 6:#color
                        r = a[1:3]
                        g = a[3:5]
                        b = a[5:]
                        color[0]= int(r, base=16)*100/255
                        color[1] = int(g, base=16)*100/255
                        color[2] = int(b, base=16)*100/255
                    if a[0] == 'z' and a[1].isdigit():#按钮文字大小
                        size = int(a[1:])
                    #字体默认y 50
                    if a == 'oy':
                        my = 0
                    if a == 'line':
                        label = 'line'
                    if a[0] == 'h' and a[1].isdigit():
                        lineH = int(a[1:])
                    if a[0] == 'a' and a[1].isdigit():#alpha 透明度是 100单位
                        color[3] = int(a[1:])
                    if a == 'flow':
                        label = 'flow'
                    if a[:2] == 'in' and a[2].isdigit():
                        itemNum = int(a[2:])
                    if a[:2] == 'rn' and a[2].isdigit():
                        rowNum = int(a[2:])
                    if a == 'dy':
                        direct = 'y'
                    if a == 'dx':
                        direct = 'x'
                    if a[:3] == 'wid':
                        WIDTH = int(a[3:])
                    if a[:3] == 'hei':
                        HEIGHT = int(a[3:])
                    if a[:4] == 'offx':
                        OFFX = int(a[4:])
                    if a[:4] == 'offy':
                        OFFY = int(a[4:])
                    if a == 'e':#导出元素到类成员变量 名字 = name 导出view 和 label
                        export = True
                    if a == 'colorLine':
                        label = 'colorLine'
                    if a == 'input':
                        label = 'input'
                    if a[:4] == 'zord' and a[4].isdigit():
                        zord = int(a[4:])
                    if a == 'sca':
                        sca = True
                    if a == 'ax':#限制x方向的区域文字
                        label = 'ax'
                    if a == 'showStar':#非全屏对话框 显示蓝色星空背景
                        label = 'showStar'
                    if a == 'altas':
                        label = 'altas'
                    if a in ['white', 'yellow', 'blue']:
                        altasColor = a
                    if a == 'right':
                        mx = 100
                    if a == 'bottom':
                        my = 100
                    if a == 'labelMx':#限制文本宽度
                        labelMx = True
                        
                        
                        

                wid = i.width
                hei = i.height

                px = i.offsets[0] - back.offsets[0]
                py = i.offsets[1] - back.offsets[1]
                INIT_X = px
                INIT_Y = py
                #字体默认 竖直居中
                if label == 'l' and my == None:
                    my = 50
                if my == None:
                    my = 0

                px += wid*mx/100
                py += hei*my/100
                head = {'l':'label', 's':'sprite'}

                px -= 512
                py = 768-py+-384
                if label in head:
                    funcHead = 'bg.add%s' % (head[label])
                    if zord != 0:
                        funcHead = head[label]

                if label == 'l':#字体似乎要增加1/4体积大小
                    sz = hei
                    if size != None:
                        sz = size
                    #查找字符串对应的key
                    name = strings.get(name, name)
                    if not export:
                        print 'bg.addlabel(getStr("%s", null), "fonts/heiti.ttf", %d).anchor(%d, %d).pos(%d, %d).color(%d, %d, %d);' % (name, sz, mx, my, px, py, color[0], color[1], color[2])
                    else:
                        print '%s = bg.addlabel(getStr("%s", null), "fonts/heiti.ttf", %d).anchor(%d, %d).pos(%d, %d).color(%d, %d, %d);' % (name, name, sz, mx, my, px, py, color[0], color[1], color[2])
                elif label == 'ax':
                    sz = hei
                    if size != None:
                        sz = size
                    print 'temp = bg.addlabel(getStr("%s", null), "fonts/heiti.ttf", %d, FONT_NORMAL, %d, 0, ALIGN_LEFT).anchor(%d, %d).pos(%d, %d).color(%d, %d, %d);' % (name, sz, wid, mx, my, px, py, color[0], color[1], color[2])
                    if export:
                        print '%s = temp;' % (name)
                #scale zord export
                elif label == 's':
                    name = curPic.get(name, name)
                    if sca != None:
                        print 'temp = %s(\"%s\").anchor(%d, %d).pos(%d, %d).color(%d, %d, %d, %d);' % (funcHead, name+'.png', mx, my, px, py, color[0], color[1], color[2], color[3]) 
                        print 'sca = getSca(temp, [%d, %d]);' % (wid, hei)
                        print 'temp.scale(sca);'
                    else:
                        print 'temp = %s(\"%s\").anchor(%d, %d).pos(%d, %d).size(%d, %d).color(%d, %d, %d, %d);' % (funcHead, name+'.png', mx, my, px, py, wid, hei, color[0], color[1], color[2], color[3]) 
                        
                    if zord != 0:
                        print 'bg.add(temp, %d);' % (zord)
                    if export:
                        print '%s = temp;' % (name)
                    """
                    if not export:
                        if zord == 0:
                            if sca != None:#限制图片大小
                                print 'temp = bg.addsprite(\"%s\").anchor(%d, %d).pos(%d, %d).color(%d, %d, %d, %d);' % (name+'.png', mx, my, px, py, color[0], color[1], color[2], color[3]) 
                                print 'sca = getSca(temp, [%d, %d]);' % (wid, hei)
                            else:
                                print 'bg.addsprite(\"%s\").anchor(%d, %d).pos(%d, %d).size(%d, %d).color(%d, %d, %d, %d);' % (name+'.png', mx, my, px, py, wid, hei, color[0], color[1], color[2], color[3]) 
                        else:
                            print 'temp = sprite(\"%s\").anchor(%d, %d).pos(%d, %d).size(%d, %d).color(%d, %d, %d, %d);' % (name+'.png', mx, my, px, py, wid, hei, color[0], color[1], color[2], color[3]) 
                            print 'bg.add(temp, %d);' % (zord)
                    else:
                        if zord == 0:
                            print '%s = bg.addsprite(\"%s\").anchor(%d, %d).pos(%d, %d).size(%d, %d).color(%d, %d, %d, %d);' % (name, name+'.png', mx, my, px, py, wid, hei, color[0], color[1], color[2], color[3]) 
                        else:
                            print '%s = sprite(\"%s\").anchor(%d, %d).pos(%d, %d).size(%d, %d).color(%d, %d, %d, %d);' % (name, name+'.png', mx, my, px, py, wid, hei, color[0], color[1], color[2], color[3]) 
                            print 'bg.add(%s, %d);' % (name, zord)
                    """
                            
                elif label == 'b':#导出按钮
                    if size == None:
                        size = 18
                    butWord = strings.get(butWord, butWord)
                    if callBack == "" and len(butWord) > 0:
                        fw = butWord[0].upper()
                        callBack = "on"+fw+butWord[1:]
                    print 'but0 = new NewButton("%s.png", [%d, %d], getStr("%s", null), null, %d, FONT_NORMAL, [100, 100, 100], %s, null);' % (curPic.get(name, name), wid, hei, butWord, size, callBack)
                    print 'but0.bg.pos(%d, %d);' % (px, py)
                    print 'addChild(but0);'
                elif label == 'line':
                    sz = hei
                    name = strings.get(name, name)
                    if size != None:
                        sz = size
                    print 'line = stringLines(getStr("%s", null), %d, %d, [%d, %d, %d], FONT_NORMAL );' % (name, sz, lineH, color[0], color[1], color[2])
                    print 'line.pos(%d, %d);' % (px, py)
                    print 'bg.add(line);'
                elif label == 'colorLine':
                    sz = hei
                    name = strings.get(name, name)
                    if size != None:
                        sz = size
                    print 'line = colorLines(getStr("%s", null), %d, %d);' % (name, sz, lineH)
                    print 'line.pos(%d, %d);' % (px, py)
                    print 'bg.add(line);'
                #需要类全局变量 处理
                elif label == 'input':
                    print 'inputView = v_create(V_INPUT_VIEW, %d, %d, %d, %d);' % (px, py, wid, hei)
                    print """
                    override function enterScene()
                    {
                        super.enterScene();
                        v_root().addview(inputView);
                    }
                    """
                    print """
                    override function exitScene()
                    {
                        inputView.removefromparent();
                        super.exitScene();
                    }
                    """
                elif label == 'flow':
                    if direct == 'y':
                        fn = 'FlowYTemplate.as'
                    elif direct == 'x':
                        fn = 'FlowXTemplate.as'
                        
                    template = os.path.join(os.environ['HOME'], 'template', fn)
                    ot = open(template, 'r')
                    tempCon = ot.read()
                    ot.close()
                    k2v = {
                        '[OFFX]': OFFX,
                        '[OFFY]': OFFY,
                        '[ITEM_NUM]': itemNum,
                        '[ROW_NUM]': rowNum,
                        '[WIDTH]': WIDTH,
                        '[HEIGHT]': HEIGHT,
                        '[PANEL_WIDTH]': wid,
                        '[PANEL_HEIGHT]': hei,
                        '[INITX]': INIT_X,
                        '[INITY]': INIT_Y
                    }
                    for k in k2v:
                        tempCon = tempCon.replace(k, str(k2v[k]))
                    outF = os.path.join(os.environ['HOME'], 'template', name)
                    newF = open(outF, 'w')
                    newF.write(tempCon)
                    newF.close()
                    print "saveFile", name
                elif label == 'showStar':
                    print 'bg.add(showFullBack());'
                elif label == 'altas':
                    print 'temp = altasWord("%s", "");' % (altasColor)
                    print 'temp.pos(%d, %d).anchor(%d, %d);' % (px, py, mx, my)
                    print 'bg.add(temp);'

#生成IOS 的 位置代码 都是相对于背景 的 960 * 640 的代码
#组件相对于对话框
def genIOSLayerCode(l, back, curPic, pdb, strings):
    SCREEN_WIDTH = 960
    SCREEN_HEIGHT = 640 
    for i in l:
        #可见性决定是否生成代码
        if i.visible:
            if hasattr(i, 'layers'):
                l = i.layers
                l.reverse()
                genIOSLayerCode(l, back, curPic, pdb, strings)
            else:
                iName = i.name.replace('＃', '#')
                attris = iName.split('#')   
                name = attris[0]
                if name[-1] == ' ':
                    name = name[:-1]
                #label = attris[1]
                label = 's'
                mx = 0
                my = None
                butWord = ""
                callBack = ""
                color = [255, 255, 255, 255]
                size = None
                lineH = 20
                alpha = 255

                itemNum = 3
                rowNum = 2
                direct = 'y'
                WIDTH = 100
                HEIGHT = 100
                OFFX = 100
                OFFY = 100
                export = False
                zord = 0
                sca = None
                labelMx = False
                #num_channels, pixel = pdb.gimp_drawable_get_pixel(i, 0, 0)#图层透明度
                #color[3] = pixel[3]*100/255
                altasColor = "white"

                for a in attris[1:]:
                    if a[-1] == ' ':
                        a = a[:-1]
                    if a == 'mx':
                        mx = 50
                    if a == 'my':
                        my = 50
                    if a == 'l':
                        label = a
                    if a == 's':
                        label = a
                    if a == 'b':
                        mx = 50
                        my = 50
                        label = 'b'
                    if a == 'mid':
                        mx = 50
                        my = 50
                    if a[0] == 'w':#按钮文字
                        butWord = a[1:]
                    if a[0] == 'c':#callback
                        callBack = a[1:]
                    if a[0] == 'r' and len(a[1:])  == 6:#color
                        r = a[1:3]
                        g = a[3:5]
                        b = a[5:]
                        color[0]= int(r, base=16)
                        color[1] = int(g, base=16)
                        color[2] = int(b, base=16)
                    if a[0] == 'z' and a[1].isdigit():#按钮文字大小
                        size = int(a[1:])
                    #字体默认y 50
                    if a == 'oy':
                        my = 0
                    if a == 'line':
                        label = 'line'
                    if a[0] == 'h' and a[1].isdigit():
                        lineH = int(a[1:])
                    if a[0] == 'a' and a[1].isdigit():#alpha 透明度是 100单位 IOS 的单位是 255
                        color[3] = int(a[1:])*255/100.0
                    if a == 'flow':
                        label = 'flow'
                    if a[:2] == 'in' and a[2].isdigit():
                        itemNum = int(a[2:])
                    if a[:2] == 'rn' and a[2].isdigit():
                        rowNum = int(a[2:])
                    if a == 'dy':
                        direct = 'y'
                    if a == 'dx':
                        direct = 'x'
                    if a[:3] == 'wid':
                        WIDTH = int(a[3:])
                    if a[:3] == 'hei':
                        HEIGHT = int(a[3:])
                    if a[:4] == 'offx':
                        OFFX = int(a[4:])
                    if a[:4] == 'offy':
                        OFFY = int(a[4:])
                    if a == 'e':#导出元素到类成员变量 名字 = name 导出view 和 label
                        export = True
                    if a == 'colorLine':
                        label = 'colorLine'
                    if a == 'input':
                        label = 'input'
                    if a[:4] == 'zord' and a[4].isdigit():
                        zord = int(a[4:])
                    if a == 'sca':
                        sca = True
                    if a == 'ax':#限制x方向的区域文字
                        label = 'ax'
                    if a == 'showStar':#非全屏对话框 显示蓝色星空背景
                        label = 'showStar'
                    if a == 'altas':
                        label = 'altas'
                    if a in ['white', 'yellow', 'blue']:
                        altasColor = a
                    if a == 'right':
                        mx = 100
                    if a == 'bottom':
                        my = 100
                    if a == 'labelMx':#限制文本宽度
                        labelMx = True
                        
                        
                        

                wid = i.width
                hei = i.height

                px = i.offsets[0] - back.offsets[0]
                py = i.offsets[1] - back.offsets[1]
                INIT_X = px
                INIT_Y = py
                #字体默认 竖直居中
                if label == 'l' and my == None:
                    my = 50
                if my == None:
                    my = 0

                px += wid*mx/100
                py += hei*my/100
                head = {'l':'label', 's':'sprite'}
                if label in head:
                    funcHead = 'bg.add%s' % (head[label])
                    if zord != 0:
                        funcHead = head[label]

                mx = mx/100.0
                my = 1.0-my/100.0

                if label == 'l':#字体似乎要增加1/4体积大小
                    sz = hei
                    if size != None:
                        sz = size
                    #查找字符串对应的key
                    name = strings.get(name, name)
                    print 'temp = CCLabelTTF:create(getStr("%s", nil), "fonts/heiti.ttf", %d)' % (name, sz)
                    print 'temp:setAnchorPoint(ccp(%d, %d))' % (mx, my)
                    print 'temp:setPosition(ccp(%d, %d))' % (px, SCREEN_HEIGHT-py)
                    print 'temp:setColor(ccc3(%d, %d, %d))' % (color[0], color[1], color[2])
                    print 'temp:setOpacity(%d)' % (color[3])
                    print 'self.bg:addChild(temp)'
                    if export:
                        print '%s = temp' % (name)
                elif label == 'ax':
                    sz = hei
                    if size != None:
                        sz = size
                    print 'temp = bg.addlabel(getStr("%s", null), "fonts/heiti.ttf", %d, FONT_NORMAL, %d, 0, ALIGN_LEFT).anchor(%d, %d).pos(%d, %d).color(%d, %d, %d);' % (name, sz, wid, mx, my, px, py, color[0], color[1], color[2])
                    if export:
                        print '%s = temp;' % (name)
                #scale zord export
                elif label == 's':
                    name = curPic.get(name, name)
                    print 'temp = CCSprite:create("%s")' % (name+'.png')
                    print 'temp:setAnchorPoint(ccp(%d, %d))' % (mx, my)
                    print 'temp:setPosition(ccp(%d, %d))' % (px, py)
                    print 'temp:setColor(ccc3(%d, %d, %d))' % (color[0], color[1], color[2])
                    print 'temp:setOpacity(%d)' % (color[3])
                    if sca != None:
                        print 'sca = getSca(temp, {%d, %d})' % (wid, hei)
                        print 'temp:setScale(sca)'
                    print 'self.bg:addChild(temp, %d)' % (zord)
                    if export:
                        print '%s = temp' % (name)
                            
                elif label == 'b':#导出按钮
                    if size == None:
                        size = 18
                    butWord = strings.get(butWord, butWord)
                    if callBack == "" and len(butWord) > 0:
                        fw = butWord[0].upper()
                        callBack = "on"+fw+butWord[1:]
                    print 'but0 = new NewButton("%s.png", [%d, %d], getStr("%s", null), null, %d, FONT_NORMAL, [100, 100, 100], %s, null);' % (curPic.get(name, name), wid, hei, butWord, size, callBack)
                    print 'but0.bg.pos(%d, %d);' % (px, py)
                    print 'addChild(but0);'
                elif label == 'line':
                    sz = hei
                    name = strings.get(name, name)
                    if size != None:
                        sz = size
                    print 'line = stringLines(getStr("%s", null), %d, %d, [%d, %d, %d], FONT_NORMAL );' % (name, sz, lineH, color[0], color[1], color[2])
                    print 'line.pos(%d, %d);' % (px, py)
                    print 'bg.add(line);'
                elif label == 'colorLine':
                    sz = hei
                    name = strings.get(name, name)
                    if size != None:
                        sz = size
                    print 'line = colorLines(getStr("%s", null), %d, %d);' % (name, sz, lineH)
                    print 'line.pos(%d, %d);' % (px, py)
                    print 'bg.add(line);'
                #需要类全局变量 处理
                elif label == 'input':
                    print 'inputView = v_create(V_INPUT_VIEW, %d, %d, %d, %d);' % (px, py, wid, hei)
                    print """
                    override function enterScene()
                    {
                        super.enterScene();
                        v_root().addview(inputView);
                    }
                    """
                    print """
                    override function exitScene()
                    {
                        inputView.removefromparent();
                        super.exitScene();
                    }
                    """
                elif label == 'flow':
                    if direct == 'y':
                        fn = 'FlowYTemplate.as'
                    elif direct == 'x':
                        fn = 'FlowXTemplate.as'
                        
                    template = os.path.join(os.environ['HOME'], 'template', fn)
                    ot = open(template, 'r')
                    tempCon = ot.read()
                    ot.close()
                    k2v = {
                        '[OFFX]': OFFX,
                        '[OFFY]': OFFY,
                        '[ITEM_NUM]': itemNum,
                        '[ROW_NUM]': rowNum,
                        '[WIDTH]': WIDTH,
                        '[HEIGHT]': HEIGHT,
                        '[PANEL_WIDTH]': wid,
                        '[PANEL_HEIGHT]': hei,
                        '[INITX]': INIT_X,
                        '[INITY]': INIT_Y
                    }
                    for k in k2v:
                        tempCon = tempCon.replace(k, str(k2v[k]))
                    outF = os.path.join(os.environ['HOME'], 'template', name)
                    newF = open(outF, 'w')
                    newF.write(tempCon)
                    newF.close()
                    print "saveFile", name
                elif label == 'showStar':
                    print 'bg.add(showFullBack());'
                elif label == 'altas':
                    print 'temp = altasWord("%s", "");' % (altasColor)
                    print 'temp.pos(%d, %d).anchor(%d, %d);' % (px, py, mx, my)
                    print 'bg.add(temp);'

#生成IOS 960 * 640 尺寸的 lua代码
def genIOSCode(p, back):
    con = MySQLdb.connect(host='localhost', user='root', passwd='badperson3', db='Wan2', charset='utf8')
    sql = 'select chinese, english from allpictures'
    con.query(sql)
    res = con.store_result().fetch_row(0, 1)#rowNum Dict
    curPic = dict([[i['chinese'].encode('utf8'), i['english'].encode('utf8')] for i in res])
    

    sql = "select * from Strings"
    con.query(sql)
    res = con.store_result().fetch_row(0, 1)#rowNum Dict
    strings = {}
    for i in res:
        strings[i['chinese'].encode('utf8')] = i['key']


    b = findL(p.layers, back)
    l = list(p.layers)
    l.reverse()
    print 'self.bg = CCNode:create()'
    print 'self:init();'
    print 'local but0'
    print 'local line'
    print 'local temp'
    print 'local sca'
    genIOSLayerCode(l, b, curPic, None, strings)
    con.close()


   
#生成unity3d NGUI 的代码
def genNGUICode(p, back, name, atlas, pdb=None):
    con = MySQLdb.connect(host='localhost', user='root', passwd='badperson3', db='uiname', charset='utf8')
    sql = 'select cnName, engName from picname'
    con.query(sql)
    res = con.store_result().fetch_row(0, 1)#rowNum Dict
    curPic = dict([[i['cnName'].encode('utf8'), i['engName'].encode('utf8')] for i in res])


    b = findL(p.layers, back)
    l = list(p.layers)
    l.reverse()
    ret = ""
    ret += "\t\tUISprite sprite;\n"
    ret += "\t\tGameObject go;\n"
    ret += "\t\tUISlicedSprite bg;\n"
    ret += "\t\tUIButtonMessage message;\n"
    ret += "\t\tGameObject rootObject;\n"
    ret += "\t\tUIDraggablePanel drag;\n"
    ret += "\t\tUIDragPanelContents dragContents;\n"
    ret += "\t\tBoxCollider box;\n"
    ret += "\t\tUIPanel panel2;\n"
    ret += "\t\tGameObject oldObject;\n"
    ret += "\t\trootObject = panel.gameObject;\n"

    newRet, depth, callbacks = genCSharpCode(l, b, curPic, pdb, {}, 0)
    ret += newRet

    callbackCode = ""
    for i in callbacks:
        callbackCode += "\tvoid %s() {\n" % (i)
        callbackCode += "\t}\n"

    f = open("G:\\gimpOutput\\template\\SpriteTemplate.cs")
    con = f.read()
    f.close()
    con = con.replace("[PANEL]", ret)
    con = con.replace("[CALLBACKS]", callbackCode)
    con = con.replace('[NAME]', name)
    con = con.replace('[ATLAS]', atlas)

    newF = open("G:\\gimpOutput\\template\\%s.cs" % (name), 'w')
    newF.write(con)
    newF.close()

            
#生成Android 800 * 480 的代码
def genImCode(p, back, pdb=None):
    con = MySQLdb.connect(host='localhost', user='root', passwd='badperson3', db='Wan2', charset='utf8')
    sql = 'select chinese, english from allpictures'
    con.query(sql)
    res = con.store_result().fetch_row(0, 1)#rowNum Dict
    curPic = dict([[i['chinese'].encode('utf8'), i['english'].encode('utf8')] for i in res])
    

    sql = "select * from Strings"
    con.query(sql)
    res = con.store_result().fetch_row(0, 1)#rowNum Dict
    strings = {}
    for i in res:
        strings[i['chinese'].encode('utf8')] = i['key']


    b = findL(p.layers, back)
    l = list(p.layers)
    l.reverse()
    print 'bg = node();'
    print 'init();'
    print 'var but0;'
    print 'var line;'
    print 'var temp;'
    print 'var sca;'
    genLayerCode(l, b, curPic, pdb, strings)
    con.close()

def getAllRel(l):
    last = l[-1]
    for i in l[:-1]:
        o0 = last.offsets
        o1 = i.offsets
        print i.name, o1[0]-o0[0], o1[1]-o0[1], i.width, i.height
def getAllLayerOffsets(im):
    for i in im.layers:
        print i.name, i.offsets

def getButPos(im, n0, n1):
    n0 = findL(im, n0)
    n1 = findL(im, n1)
    o0 = n0.offsets
    o1 = n1.offsets
    print o1[0]-o0[0]+n1.width/2, o1[1]-o0[1]+n1.height/2, n1.width, n1.height

def getAllOff(im, b, e):
    #im = gimp.image_list()[0]
    bp = 0
    ep = 0
    curP = 0
    for i in im.layers:
        print i.name
        if i.name == b:
            bp = curP
        elif i.name == e:
            ep = curP
            break
        curP += 1
    
    lays = im.layers[bp:ep+1]
    print bp, ep
    return lays

def getAllVisible(l):
    res = []
    for i in l:
        if i.visible:
            res.append(i)
            print i.name, i.offsets, i.width, i.height
    return res

def genCode(l):
    v = getAllVisible(l)
    v.reverse()
    print 'bg = node();'
    print 'init();'
    for i in v:
        print 'bg.addsprite("%s").pos(%d, %d).size(%d, %d)' % (i.name+".png", i.offsets[0], i.offsets[1], i.width, i.height)
            

def getColor(r, g, b):
    print r*100/255, g*100/255, b*100/255
#pdb 库 图层的名字 存储目录
#删除内部image

#遍历所有可见图层 并导出

            

#新的图片大小需要和原图片大小相同
#拷贝图层到新的图片的相同位置接着存储图片
"""
image = pdb.gimp_image_new(p.width, p.height, 0)
新建图层
 layer = pdb.gimp_layer_new(image, l.width, l.height, 1, "test", 100, 0)
添加图层
 pdb.gimp_image_add_layer(image, layer, 0)
拷贝原图层
 non_empty = pdb.gimp_edit_copy(l)
复制到新图层上 不要选择
floating_sel = pdb.gimp_edit_paste(layer, FALSE)
删除浮动选择
pdb.gimp_floating_sel_remove(floating_sel)


#复制图层
layer_copy = pdb.gimp_layer_new_from_drawable(l, image)
#粘贴到image中
pdb.gimp_image_add_layer(image, layer_copy, 0)
"""
def saveSamePosAndSizeWithImage(pdb, l):
    non_empty = pdb.gimp_edit_copy(l)
    oldIm = l.image
    image = pdb.gimp_image_new(oldIm.width, oldIm.height, 0)
    layer = pdb.gimp_layer_new(image, image.width, image.height, 1, "test", 100, 0)
    pdb.gimp_image_add_layer(image, layer, 0)

    layer_copy = pdb.gimp_layer_new_from_drawable(l, image)
    pdb.gimp_image_add_layer(image, layer_copy, 0)

    layer = pdb.gimp_image_merge_visible_layers(image, 1)

    n = l.name.split('#')[0]
    if n[-1] == ' ':#去除名字末尾空格
        n = n[:-1]
    print 'saveAni', n, oldIm.width, oldIm.height, layer.width, layer.height
    
    pdb.gimp_file_save(image, layer, os.environ['HOME']+"/temp/animation/"+n+".png", "")
    #pdb.file_png_save(image, image.layers[0], os.environ['HOME']+"/temp/animation/"+n+".png", "nn", 0, 9, 0, 0, 0, 0, 0)
    pdb.gimp_image_delete(image)

def saveEquips(pdb, l):
    con = MySQLdb.connect(host='localhost', user='root', passwd='badperson3', db='Wan2', charset='utf8')
    sql = 'insert into newEquip (`name`)  values(\'%s\')' % (l.name)
    con.query(sql)
    #res = con.store_result().fetch_row(0, 1)#rowNum Dict
    con.commit()
    con.close()

    non_empty = pdb.gimp_edit_copy(l)
    oldIm = l.image
    image = pdb.gimp_image_new(oldIm.width, oldIm.height, 0)
    layer = pdb.gimp_layer_new(image, image.width, image.height, 1, "test", 100, 0)
    pdb.gimp_image_add_layer(image, layer, 0)

    layer_copy = pdb.gimp_layer_new_from_drawable(l, image)
    pdb.gimp_image_add_layer(image, layer_copy, 0)

    layer = pdb.gimp_image_merge_visible_layers(image, 1)

    n = l.name.split('#')[0]
    if n[-1] == ' ':#去除名字末尾空格
        n = n[:-1]
    print 'saveAni', n, oldIm.width, oldIm.height, layer.width, layer.height
    
    pdb.gimp_file_save(image, layer, os.environ['HOME']+"/temp/equips/"+n+".png", "")
    #pdb.file_png_save(image, image.layers[0], os.environ['HOME']+"/temp/animation/"+n+".png", "nn", 0, 9, 0, 0, 0, 0, 0)
    pdb.gimp_image_delete(image)


def exportEquips(pdb, p):
    for i in p.layers:
        #if i.visible:
        if hasattr(i, 'layers'):
            exportEquips(pdb, i)
        else:
            saveEquips(pdb, i)


def saveDrug(pdb, l):
    con = MySQLdb.connect(host='localhost', user='root', passwd='badperson3', db='Wan2', charset='utf8')
    sql = 'insert into newDrug (`name`)  values(\'%s\')' % (l.name)
    con.query(sql)
    #res = con.store_result().fetch_row(0, 1)#rowNum Dict
    con.commit()
    con.close()

    non_empty = pdb.gimp_edit_copy(l)
    oldIm = l.image
    image = pdb.gimp_image_new(oldIm.width, oldIm.height, 0)
    layer = pdb.gimp_layer_new(image, image.width, image.height, 1, "test", 100, 0)
    pdb.gimp_image_add_layer(image, layer, 0)

    layer_copy = pdb.gimp_layer_new_from_drawable(l, image)
    pdb.gimp_image_add_layer(image, layer_copy, 0)

    layer = pdb.gimp_image_merge_visible_layers(image, 1)

    n = l.name.split('#')[0]
    if n[-1] == ' ':#去除名字末尾空格
        n = n[:-1]
    print 'saveAni', n, oldIm.width, oldIm.height, layer.width, layer.height
    
    pdb.gimp_file_save(image, layer, os.environ['HOME']+"/temp/drugs/"+n+".png", "")
    #pdb.file_png_save(image, image.layers[0], os.environ['HOME']+"/temp/animation/"+n+".png", "nn", 0, 9, 0, 0, 0, 0, 0)
    pdb.gimp_image_delete(image)

def exportDrug(pdb, p):
    for i in p.layers:
        if hasattr(i, 'layers'):
            exportDrug(pdb, i)
        else:
            saveDrug(pdb, i)

#拷贝建筑物到 新的Image中去
def saveBuild(pdb, l, red2, shadow2, featureColor):
    image = pdb.gimp_image_new(l.width, l.height, 0)
    #buildLayer = l.layers[0]
    shadowPos = [0, 0]
    shadowSize = [0, 0]
    k = 0
    for i in l.layers:
        layer_copy = pdb.gimp_layer_new_from_drawable(i, image)
        if k == 0:
            buildLayer = layer_copy
        pdb.gimp_image_add_layer(image, layer_copy, 0)
        pdb.gimp_layer_set_offsets(layer_copy, i.offsets[0]-l.offsets[0], i.offsets[1]-l.offsets[1])
        pdb.gimp_layer_set_opacity(layer_copy, 100)
        if i.name.find('阴影') != -1:
            shadowPos = i.offsets[0]-l.offsets[0], i.offsets[1]-l.offsets[1]
            shadowSize = [i.width, i.height]
        elif i.name.find('特征色') != -1:
            featureColorPos = i.offsets[0]-l.offsets[0], i.offsets[1]-l.offsets[1]
            featureColorSize = [i.width, i.height]
        k += 1


    layer_copy = pdb.gimp_layer_new_from_drawable(red2, image)
    pdb.gimp_image_add_layer(image, layer_copy, 0)
    pdb.gimp_layer_set_offsets(layer_copy, l.width/2-layer_copy.width/2, l.height-layer_copy.height)

    layer_copy = pdb.gimp_layer_new_from_drawable(shadow2, image)
    pdb.gimp_image_add_layer(image, layer_copy, 0)
    pdb.gimp_layer_set_offsets(layer_copy, shadowPos[0]+shadowSize[0]/2-layer_copy.width/2, shadowPos[1]+shadowSize[1]/2-layer_copy.height/2)
    pdb.gimp_layer_set_opacity(layer_copy, 100)

    """
    layer_copy = pdb.gimp_layer_new_from_drawable(featureColor, image)
    pdb.gimp_image_add_layer(image, layer_copy, 0)
    pdb.gimp_layer_set_offsets(layer_copy, featureColorPos[0]+featureColorSize[0]/2-layer_copy.width/2, featureColorPos[1]+featureColorSize[1]/2-layer_copy.height/2)
    """

    layer_copy = pdb.gimp_layer_copy(buildLayer, 0)
    pdb.gimp_image_add_layer(image, layer_copy, 0)
    item = pdb.gimp_item_transform_flip_simple(layer_copy, 0, True, l.width/2)


        
    display = pdb.gimp_display_new(image)
    return image
def searchLayer(p, name):
    #print p.name, name
    if p.name.find(name) != -1:
        return [p]

    #print p.name.find(name)
    ret = []
    for i in p.layers:
        if i.visible:
        #print i.name
            if hasattr(i, 'layers'):
                ret += searchLayer(i, name)
            else:
                if i.name.find(name) != -1:
                    ret.append(i)
    return ret
#导出优化10-22建筑物图片
#同时拷贝水晶矿 ab 两个图层的对象
#调整方法：
#   建筑物 和 底座居中 手动调整 a号建筑位置
#   调整建筑物的位置 根据背景图 反转 adjustPos
#   保存导出建筑物 exportBuild

#copyBuild pdb, p, 民居 第一个方向 a 接着第二个方向是b
#将建筑 阴影 red2 特征色图片 拷贝到 新的image中去
#将主建筑 水平flip拷贝一份
#将主建筑的阴影 a b 两个 建筑的阴影 

#a 将主建筑放到 最高位置 特征色 阴影
#b 阴影
def copyBuild(pdb, p, name):
    #print name, p.name
    allGroup = searchLayer(p, name)
    red2 = findL(p.layers, 'red2')
    featureColor = None
    print len(allGroup)
    for i in allGroup:
        print i.name
    #只在b里面找不在a里面找图片
    for i in allGroup:
        if i.name.find('a') != -1:
            mainL = i
        else:
            for l in i.layers:
                if l.name.find('阴影') != -1:
                    shadow2 = l
                #elif l.name.find('特征色') != -1:
                #    featureColor = l
            #break
        #else:

    print mainL, red2, shadow2, featureColor
    image = saveBuild(pdb, mainL, red2, shadow2, featureColor)
    #drawable = pdb.gimp_image_get_active_drawable(image)
    #pdb.gimp_xcf_save(0, image, drawable, os.environ['HOME']+"/temp/build/"+name+".xcf", name+".xcf")
    return image

def notVisible(pdb, im):
    pdb.gimp_item_set_visible(im, False)
    for i in im.layers:
        if hasattr(i, 'layers'):
            notVisible(pdb, i)
        else:
            pdb.gimp_item_set_visible(i, False)
#最后一个图层是原建筑
#第一个图层是复制并转向的建筑
def adjustPos(pdb, p):
    ori = p.layers[-1]
    leftWidth = (ori.width - (p.width/2-ori.offsets[0]))
    offx = p.width/2-leftWidth
    pdb.gimp_layer_set_offsets(p.layers[0], offx, ori.offsets[1])
            
#导出建筑物的图层 建筑物 阴影
#主建筑 a 没有#符号
#阴影 包含阴影文字 和 a b 编号
#特征色
def exportBuild(pdb, im, pid):
    #导出每个图层 名字和id
    for i in im.layers:
        if i.name.find('red2') == -1 and i.name.find('阴影') == -1 and i.name.find('#') == -1 and i.name.find('特征色') == -1:
            pdb.gimp_layer_resize_to_image_size(i)
            pdb.file_png_save(im, i, os.environ['HOME']+"/temp/build/build"+str(pid)+".png", "nn", 0, 9, 0, 0, 0, 0, 0)
        elif i.name.find('阴影') != -1:
            if i.name.find('a') != -1:
                pdb.gimp_layer_resize_to_image_size(i)
                pdb.file_png_save(im, i, os.environ['HOME']+"/temp/build/build"+str(pid)+"Shadow0.png", "nn", 0, 9, 0, 0, 0, 0, 0)
            elif i.name.find('b') != -1:
                pdb.gimp_layer_resize_to_image_size(i)
                pdb.file_png_save(im, i, os.environ['HOME']+"/temp/build/build"+str(pid)+"Shadow1.png", "nn", 0, 9, 0, 0, 0, 0, 0)
        elif i.name.find('特征色') != -1:
                pdb.gimp_layer_resize_to_image_size(i)
                pdb.file_png_save(im, i, os.environ['HOME']+"/temp/build/build"+str(pid)+"_f.png", "nn", 0, 9, 0, 0, 0, 0, 0)
            
                
                

            
    


#中文图片存储到temp
def saveLayer(pdb, l, curPic):
    non_empty = pdb.gimp_edit_copy(l)
    image = pdb.gimp_edit_paste_as_new()
    n = l.name.split('#')[0]
    if n[-1] == ' ':#去除名字末尾空格
        n = n[:-1]
    print 'saveNormal', n
    newName = curPic.get(n, n)
    pdb.file_png_save(image, image.layers[0], "G:\\gimpOutput\\"+newName+".png", "nn", 0, 9, 0, 0, 0, 0, 0)
    pdb.gimp_image_delete(image)
#不切割图片
def checkAniSave(pdb, im):
    ret = [] 
    for i in im.layers:
        if i.visible:
            if hasattr(i, 'layers'):
                ret += checkAniSave(pdb, i)
            else:
                iName = i.name.replace('＃', '#')
                attris = iName.split('#')   
                name = attris[0]
                if name[-1] == ' ':
                    name = name[:-1]

                saveSamePosAndSizeWithImage(pdb, i)
                ret.append(i.name)
    return ret

#中文图片存储到temp
def saveInLayer(pdb, l):
    non_empty = pdb.gimp_edit_copy(l)
    image = pdb.gimp_edit_paste_as_new()
    n = l.name.split('#')[0]
    if n[-1] == ' ':#去除名字末尾空格
        n = n[:-1]
    print 'saveNormal', n
    pdb.file_png_save(image, image.layers[0], "G:\\gimpOutput\\"+n+".png", "nn", 0, 9, 0, 0, 0, 0, 0)
    pdb.gimp_image_delete(image)
    
#保存文件到 ani 文件夹
def checkSaveInAni(pdb, im):
    ret = [] 
    for i in im.layers:
        if i.visible:
            if hasattr(i, 'layers'):
                ret += checkSaveInAni(pdb, i)
            else:
                iName = i.name.replace('＃', '#')
                attris = iName.split('#')   
                name = attris[0]
                if name[-1] == ' ':
                    name = name[:-1]

                saveInLayer(pdb, i)
                ret.append(i.name)
    return ret

#存储所有可见图层
#使用英文名称 转化图片名称
#NGUI 使用
def checkAllSave(pdb, im):
    con = MySQLdb.connect(host='localhost', user='root', passwd='badperson3', db='uiname', charset='utf8')
    sql = 'select cnName, engName from picname'
    con.query(sql)
    res = con.store_result().fetch_row(0, 1)#rowNum Dict

    curPic = dict([[i['cnName'].encode('utf8'), i['engName'].encode('utf8')] for i in res])
    con.close()

    ret = [] 
    for i in im.layers:
        if i.visible:
            if hasattr(i, 'layers'):
                ret += checkAllSave(pdb, i)
            else:
                iName = i.name.replace('＃', '#')
                attris = iName.split('#')   
                name = attris[0]
                if name[-1] == ' ':
                    name = name[:-1]

                saveLayer(pdb, i, curPic)
                ret.append(i.name)
    return ret
            
#存储#n属性的图层
def checkNSave(pdb, im):
    ret = []
    for i in im.layers:
        if i.visible:
            if hasattr(i, 'layers'):
                ret += checkNSave(pdb, i)
            else:
                iName = i.name.replace('＃', '#')
                attris = iName.split('#')   
                name = attris[0]
                if name[-1] == ' ':
                    name = name[:-1]
                #save = False
                #模板中所有图片都要保存
                save = False
                saveAni = False
                for j in attris[1:]:
                    #print j
                    if j == 'n':
                        save = True
                        ret.append(i.name)
                        #break
                    if j == 'ani':
                        saveAni = True
                    #if j == 'jpg':
                    #    i.jpg = True

                #for j in attris[1:]:
                #    if j == 'jpg':
                #        i.jpg = True
                #        break

                if save:
                    #print 'saveNow', name, saveAni
                    if saveAni:
                        saveSamePosAndSizeWithImage(pdb, i)
                    else:
                        saveLayer(pdb, i)
                
    return ret

#获得所有图层的名称
def saveMySqlName(im):
    ret = []
    for i in im.layers:
        if i.visible:
            if hasattr(i, 'layers'):
                ret += saveMySqlName(i)
            else:
                iName = i.name.replace('＃', '#')
                attris = iName.split('#')   
                name = attris[0]
                if name[-1] == ' ':
                    name = name[:-1]
                save = False
                jpg = False

                #模板中所有文件保存
                for j in attris[1:]:
                    if j == 'jpg':
                        #save = True
                        #ret.append(name)
                        jpg = True
                        break
                ret.append([name, jpg])
    return ret
#只存储标记#n的图片 名字到数据库中
def saveInPic(im):
    ret = []
    for i in im.layers:
        if i.visible:
            if hasattr(i, 'layers'):
                ret += saveInPic(i)
            else:
                iName = i.name.replace('＃', '#')
                attris = iName.split('#')   
                name = attris[0]
                if name[-1] == ' ':
                    name = name[:-1]
                save = False
                jpg = False

                #模板中所有文件保存
                for j in attris[1:]:
                    if j == 'jpg':
                        #save = True
                        #ret.append(name)
                        jpg = True
                    elif j == 'n':
                        save = True
                if save:
                    ret.append([name, jpg])
    return ret
#只存储 标记 n 的图片
def saveInPicSql(im):
    con = MySQLdb.connect(host='localhost', user='root', passwd='badperson3', db='Wan2', charset='utf8')
    sql = 'select chinese, english from allpictures'
    con.query(sql)
    res = con.store_result().fetch_row(0, 1)#rowNum Dict

    curPic = dict([[i['chinese'].encode('utf8'), i['english'].encode('utf8')] for i in res])


    names = saveInPic(im)
    for i in names:
        if curPic.get(i[0]) != None:
            print "same name", i
        else:
            #try:
            print 'save', i[0]
            sql = "insert into allpictures (chinese, english, jpg) values('%s', '%s', %d)" % (i[0], i[0], i[1])
            con.query(sql)
            #except:
            #    print 'error', sql
    
    con.commit()
    con.close()
    return names
    
    
    
#存储 所有的图片的名字到数据库中
#NGUI 
def saveNName(im):
    con = MySQLdb.connect(host='localhost', user='root', passwd='badperson3', db='uiname', charset='utf8')
    sql = 'select cnName, engName from picname'
    con.query(sql)
    res = con.store_result().fetch_row(0, 1)#rowNum Dict

    curPic = dict([[i['cnName'].encode('utf8'), i['engName'].encode('utf8')] for i in res])


    names = saveMySqlName(im)
    for i in names:
        if curPic.get(i[0]) != None:
            print "same name", i
        else:
            sql = "insert ignore into picname (cnName, engName, jpg) values('%s', '%s', %d)" % (i[0], i[0], i[1])
            con.query(sql)
            #except:
            #    print 'error', sql
    
    con.commit()
    con.close()
    return names
            
                
def checkLayer(im, curPic):
    ret = []
    for i in im.layers:
        if i.visible:
            if hasattr(i, 'layers'):
                ret += checkLayer(i, curPic)
            else:
                iName = i.name.replace('＃', '#')
                attris = iName.split('#')   
                name = attris[0]
                if name[-1] == ' ':
                    name = name[:-1]
                label = 's'
                for i in attris[1:]:
                    if i[-1] == ' ':#去除末尾空格
                        i = i[:-1]
                    if i == 'l':
                        label = 'l'
                    if i == 'b':
                        label = 'b'
                if label == 's':#图片类型
                    if not curPic.get(name, None):#没有该图层
                        ret.append(name)
    return ret

#检查 所有数据库中没有的 图片 就存储
def checkPic(im):
    con = MySQLdb.connect(host='localhost', user='root', passwd='badperson3', db='Wan2', charset='utf8')
    sql = 'select chinese, english from allpictures'
    con.query(sql)
    res = con.store_result().fetch_row(0, 1)#rowNum Dict

    curPic = dict([[i['chinese'].encode('utf8'), i['english'].encode('utf8')] for i in res])
    ret = checkLayer(im, curPic)#去除重复名字
    check = set()
    temp = []
    for i in ret:
        if i not in check:
            temp.append(i)
            check.add(i)

    print len(temp)
    for i in temp:
        try:
            sql = "insert into allpictures values('%s', '')" % (i)
            con.query(sql)
        except:
            print sql
    con.commit()
    con.close()
    return temp
    
def adjustMovePic(pdb, p):
    pdb.gimp_layer_scale(p.layers[0], 70, 70, 0)
    pdb.gimp_layer_set_offsets(p.layers[0], 11, 24)



