import sys, time, numpy as np, torch
from PIL import Image
from scipy import ndimage
S='/workspace/pixel-mascot/'; O='/workspace/in/'
def prep(path, box, name, flip=False):
    c=Image.open(path).convert('RGB').crop(box); a=np.asarray(c).astype(int)
    ys,xs=np.where(a.sum(2)<720); c=c.crop((xs.min(),ys.min(),xs.max()+1,ys.max()+1))
    s=int(max(c.size)*1.15); o=Image.new('RGB',(s,s),(255,255,255)); o.paste(c,((s-c.size[0])//2,(s-c.size[1])//2))
    o=o.resize((1024,1024),Image.LANCZOS); a=np.asarray(o).astype(int)
    lab,n=ndimage.label(a.min(2)>200)
    edge=set(lab[0].tolist())|set(lab[-1].tolist())|set(lab[:,0].tolist())|set(lab[:,-1].tolist()); edge.discard(0)
    bg=np.isin(lab,list(edge)); bg=ndimage.binary_dilation(bg,iterations=1)
    al=ndimage.gaussian_filter((~bg).astype(float),0.8)
    rgba=np.dstack([np.asarray(o),(al*255).astype(np.uint8)]); im=Image.fromarray(rgba,'RGBA')
    if flip: im=im.transpose(Image.FLIP_LEFT_RIGHT)
    im.save(O+name+'.png'); return im
orig=S+'reference/pixel-turnaround-original.jpg'; sheet=S+'turnaround/pixel-turnaround-sheet.jpg'
front=prep(orig,(280,20,860,670),'front')
side=prep(orig,(1060,20,1620,670),'side')
sidef=prep(orig,(1060,20,1620,670),'side_flip',True)
back=prep(sheet,(990,110,1260,530),'back')
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
pipe=Hunyuan3DDiTFlowMatchingPipeline.from_pretrained('tencent/Hunyuan3D-2mv',subfolder='hunyuan3d-dit-v2-mv',variant='fp16')
variants={'A_front_left_back':{'front':front,'left':sidef,'back':back},
          'B_front_right_back':{'front':front,'right':side,'back':back},
          'C_front_left':{'front':front,'left':sidef}}
for name,imgs in variants.items():
    for seed in (12345,7):
        t=time.time()
        m=pipe(image=dict(imgs),num_inference_steps=50,octree_resolution=380,num_chunks=20000,generator=torch.manual_seed(seed),output_type='trimesh')[0]
        m.export(f'/workspace/out/{name}_s{seed}.glb'); print(name,seed,len(m.vertices),len(m.faces),m.bounds.tolist(),round(time.time()-t,1),flush=True)
print('GEN_DONE')
