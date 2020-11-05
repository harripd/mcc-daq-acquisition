import time

import threading
import atexit
import numpy as np

from vispy import app, scene, gloo, visuals
# from vispy.util.filter import gaussian_filter


rolling_tex = """                                     
float rolling_texture(vec2 pos) {                     
    if( pos.x < 0 || pos.x > 1 || pos.y < 0 || pos.y >     1 ) {                    
        return 0.0f;                                  
    }                                                 
    vec2 uv = vec2(mod(pos.x+$shift, 1), pos.y);      
    return texture2D($texture, uv).r;                 
}                                                     
"""                                                   
                                                      
cmap = """                                            
vec4 colormap(float x) {                              
    x = x - 1e4;                                      
    return vec4(x/5e6, x/2e5, x/1e4, 1);              
}                                                     
"""                                                   


class ScrollingImage(scene.Image):
    def __init__(self, shape, parent): 
        self._shape = shape                                                     
        self._color_fn = visuals.shaders.Function(rolling_tex)                  
        self._ctex = gloo.Texture2D(np.zeros(shape+(1,), dtype='float32'),      
                                    format='luminance', internalformat='r32f')  
        self._color_fn['texture'] = self._ctex                                  
        self._color_fn['shift'] = 0                                             
        self.ptr = 0                                                            
        scene.Image.__init__(self, method='impostor', parent=parent)            
        # self.set_gl_state('additive', cull_face=False)                        
        self.shared_program.frag['get_data'] = self._color_fn                   
        cfun = visuals.shaders.Function(cmap)                                   
        self.shared_program.frag['color_transform'] = cfun                      

    @property                                                                   
    def size(self):                                                             
        return self._shape                                                      
                                                                                
    def roll(self, data):                                                       
        data = data.reshape(data.shape[0], 1, 1)                                
                                                                                
        self._ctex[:, self.ptr] = data                                          
        self._color_fn['shift'] = (self.ptr+1) / self._shape[1]                 
        self.ptr = (self.ptr + 1) % self._shape[1]                              
        self.update()                                                           
                                                                                
    def _prepare_draw(self, view):                                              
        if self._need_vertex_update:                                            
            self._build_vertex_data()                                           
                                                                                
        if view._need_method_update:                                            
            self._update_method(view)                                           
 

# 2000 height? well maybe..?
# SAMPLES_PER_SECOND / 250 (?)
HEIGHT = 1000

def visualize(buf, ctrdev, SAMPLES_PER_SECOND, bufsize):

    win = scene.SceneCanvas(keys='interactive', show=True, fullscreen=False)
    grid = win.central_widget.add_grid()

    view3 = grid.add_view(row=0, col=0, camera='panzoom', border_color='grey')

    #image = ScrollingImage((SAMPLES_PER_SECOND*5, HEIGHT), parent=view3.scene)
    image = ScrollingImage((bufsize, HEIGHT), parent=view3.scene)
    view3.camera.rect = (0, 0, image.size[0], image.size[1])
    gridlines = scene.GridLines(color=(1, 1, 1, 1), parent=image)

    def makebar(i):
        z = np.zeros((HEIGHT,), dtype=np.float32)
        z[0:i] = 1800000 # TODO: fix colormap to get rid of this
        return z

    last_update_idx = 0
    def update(ev):
        nonlocal last_update_idx
        (_, transferstatus) = ctrdev.get_scan_status()
        transfer_idx = transferstatus.current_index - 1

        if(transfer_idx < last_update_idx):
            for i in range(last_update_idx, bufsize):
                image.roll(makebar(buf[i]))
            last_update_idx = 0
        for i in range(0, transfer_idx):
            image.roll(makebar(buf[i]))
        last_update_idx = transfer_idx


    timer = app.Timer(interval='auto', connect=update)
    timer.start()
    app.run()

"""
    print(last_valid_index)
    for i in range(last_valid_index):
        print(buf[i], end=',')
"""