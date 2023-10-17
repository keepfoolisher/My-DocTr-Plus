from GeoTr import GeoTr

import torch
import torch.nn as nn
import torch.nn.functional as F
import skimage.io as io
import numpy as np
import cv2
import glob
import os
from PIL import Image
import argparse
import warnings
warnings.filterwarnings('ignore')



        

def reload_model(model, path=""):
    if not bool(path):
        return model
    else:
        model_dict = model.state_dict()
        pretrained_dict = torch.load(path, map_location='cuda:0')
        print(len(pretrained_dict.keys()))
        print(len(pretrained_dict.keys()))
        model_dict.update(pretrained_dict)
        model.load_state_dict(model_dict)

        return model
        

def rec(opt):
    # print(torch.__version__) # 1.5.1
    img_list = os.listdir(opt.distorrted_path)  # distorted images list

    if not os.path.exists(opt.gsave_path):  # create save path
        os.mkdir(opt.gsave_path)
    
    class GeoTrP(nn.Module):
        def __init__(self):
            super(GeoTrP, self).__init__()
            self.GeoTr = GeoTr()
            
        def forward(self, x):
            bm = self.GeoTr(x) #[0]
            bm = 2 * (bm / 288) - 1

            bm = (bm + 1) / 2 * 2560

            bm = F.interpolate(bm, size=(2560, 2560), mode='bilinear', align_corners=True)
            
            return bm


    _GeoTrP = GeoTrP()
    _GeoTrP = _GeoTrP.cuda()
    # reload geometric unwarping model
    reload_model(_GeoTrP.GeoTr, opt.GeoTr_path)
    
    # To eval mode
    _GeoTrP.eval()
  
    for img_path in img_list:
        name = img_path.split('.')[-2]  # image name

        img_path = opt.distorrted_path + img_path  # read image and to tensor
        im_ori = cv2.imread(img_path) / 255.
        h_,w_,c_ = im_ori.shape
        im_ori = cv2.resize(im_ori, (2560, 2560))

        h, w, _ = im_ori.shape
        im = cv2.resize(im_ori, (288, 288))
        im = im.transpose(2, 0, 1)
        im = torch.from_numpy(im).float().unsqueeze(0)
        
        with torch.no_grad():
            # geometric unwarping
            bm = _GeoTrP(im.cuda())
            bm = bm.cpu().numpy()[0]
            bm0 = bm[0, :, :]
            bm1 = bm[1, :, :]
            bm0 = cv2.blur(bm0, (3, 3))
            bm1 = cv2.blur(bm1, (3, 3))

            img_geo = cv2.remap(im_ori, bm0, bm1, cv2.INTER_LINEAR)*255
            img_geo = cv2.resize(img_geo, (w_, h_))
            cv2.imwrite(opt.gsave_path + name + '_geo' + '.png', img_geo.astype(np.uint8))  # save

        print('Done: ', img_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--distorrted_path',  default='./distorted/')
    parser.add_argument('--gsave_path',  default='./rectified/')
    parser.add_argument('--GeoTr_path',  default='./model_save/model.pt')
    
    opt = parser.parse_args()

    rec(opt)


if __name__ == '__main__':
    main()
