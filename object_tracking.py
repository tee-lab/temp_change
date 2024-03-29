import numpy as np
import cv2
import sys
import pandas as pd
import pickle
import math as m
import tkinter
import csv, glob
from yolo_tracker import yoloTracker
import yaml
# from utils.utils import md5check

with open("config.yml", "r") as stream:
    config_data= yaml.safe_load(stream)
root_dir = config_data["root_dir"]
grabsize = int(config_data["annotation_size"])
runtype=int(config_data["run"])
path = config_data["root_dir"]
#Open video fileimport Tkinter
from tkinter.filedialog import askopenfilename
#Open the video file which needs to be processed
root = tkinter.Tk()

#get screen resolution
screen_width = int(root.winfo_screenwidth())
screen_height = int(root.winfo_screenheight())

movieName =  askopenfilename(filetypes=[("Video files","*")])
cap = cv2.VideoCapture(movieName)

nframe =cap.get(cv2.CAP_PROP_FRAME_COUNT)
nx = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
ny = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
# Craete data frames to store x and y coords of the identified blobs, rows for each individual column for each frame
df = pd.DataFrame(columns=['c_id','x_px','y_px','frame'])
data = pd.DataFrame(columns= ['frame', 'lx', 'ty', 'rx', 'by', 'id'])
i=0
row = 0
steps=1
alt = 100#int(input("Enter height of video(integer):  "))
# work out size of box if box if 32x32 at 100m
grabSize = int(m.ceil((100/alt)*12))
#Load model
from keras.models import load_model
if runtype == 1:
  bb_model = load_model(path + "/classifiers/mothe_model.h5py")
else if runtype == 0:
  modelname = input("Enter data name (for wasp data enter wasp, for blackbuck enter bb):")
  if modelname == "wasp":
     bb_model = load_model(path + "/classifiers/wasp_model.h5py")
  else if modelname == "bb":
     bb_model = load_model(path + "/classifiers/bb_model.h5py")
#Video writer object
out = cv2.VideoWriter(root_dir+'/video_track.avi',cv2.VideoWriter_fourcc('M','J','P','G'), 24, (nx,ny))
tracker = yoloTracker(max_age=20, track_threshold=0.6, init_threshold=0.8, init_nms=0.0, link_iou=0.1)

#Define a distance function
def distance(point1, point2):
  dist=m.sqrt(((point1[0]-point2[0])**2)+((point1[1]-point2[1])**2))
  return dist
lx=[]
ty=[]
rx=[]
by=[]
uid=[]
frameid=[]

while(cap.isOpened() & (i<(nframe-steps))):

  i = i + steps
  print("[UPDATING.....]{}th/{} frame detected and stored".format(i, nframe))
  cap.set(cv2.CAP_PROP_POS_FRAMES,i)
  ret, frame = cap.read()
  grayF = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  #Equalize image
  #gray = cv2.equalizeHist(gray)
  #remove noise
  gray = cv2.medianBlur(grayF,5)
  #Invert image
  gray = cv2.bitwise_not(gray)

  # Blob detection
  # Setup SimpleBlobDetector parameters.
  params = cv2.SimpleBlobDetector_Params()

  # Change thresholds
  params.minThreshold = 100;
  params.maxThreshold = 250;

  # Filter by Circularity
  params.filterByCircularity = False
  #params.minCircularity = 0.1

  # Filter by Convexity
  params.filterByConvexity = False
  #params.minConvexity = 0.87

  # Filter by Inertia
  params.filterByInertia = False

  # Create a detector with the parameters
  ver = (cv2.__version__).split('.')
  if int(ver[0]) < 3 :
    detector = cv2.SimpleBlobDetector(params)
  else :
    detector = cv2.SimpleBlobDetector_create(params)

  # Detect blobs.
  keypoints = detector.detect(gray)

  testX = np.ndarray(shape=(len(keypoints),40,40,3), dtype='uint8', order='C')
  j = 0
  for keyPoint in keypoints:

    ix = keyPoint.pt[0]
    iy = keyPoint.pt[1]
    #Classification: here draw boxes around keypints and classify them using svmClassifier
    tmpImg=frame[max(0,int(iy-grabsize)):min(ny,int(iy+grabsize)), max(0,int(ix-grabsize)):min(nx,int(ix+grabsize))].copy()

    tmpImg1=cv2.resize(tmpImg,(40,40))
    testX[j,:,:,:]=tmpImg1
    j = j + 1
  testX = testX.reshape(-1, 40,40, 3)
  testX = testX.astype('float32')
  testX = testX / 255.
  pred = bb_model.predict(testX)
  Pclass = np.argmax(np.round(pred),axis=1)
  track_class=[]
  for certainty in pred:
    track_class.append(certainty[1])
  tictac=[]
  for tic, tac in zip(Pclass, track_class):
    tictac.append([tic, tac])
  #print(tictac)
  #print((Pclass),(track_class))
  j=0
  indx=[]
  FKP = []
  detection= []
  confidence= []
  for pr in tictac:
      if pr[0] == 1:
          row = row + 1
          df.loc[row] = [j, keypoints[j].pt[0],keypoints[j].pt[1], i]
          FKP.append(keypoints[j])
          detection.append((keypoints[j], pr[1]))

          indx.append(j)

      j=j+1

  pts=[(m.floor(i.pt[0]), m.floor(i.pt[1])) for i in FKP]
  detections= [(m.floor(i.pt[0])-grabsize, m.floor(i.pt[1])-grabsize, m.floor(i.pt[0])+grabsize,m.floor(i.pt[1])+grabsize, j) for i, j in detection]
#  print(detections)
  tracks = tracker.update(np.asarray(detections))
  save_output= True
  full_warp = np.eye(3, 3, dtype=np.float32)

  for ids in tracks:
    np.random.seed(int(ids[4])) # show each track as its own colour - note can't use np random number generator in this code
    r = np.random.randint(256)
    g = np.random.randint(256)
    b = np.random.randint(256)
    lx.append(ids[0])
    ty.append(ids[1])
    rx.append(ids[2])
    by.append(ids[3])
    uid.append(ids[4])
    frameid.append(i)
    cv2.rectangle(frame,(int(ids[0]), int(ids[1])), (int(ids[2]), int(ids[3])),(b,g,r), 2)
    cv2.putText(frame, str(int(ids[4])),(int(ids[2])+5, int(ids[3])-5),0, 5e-3 * 200, (b, g, r),2)

  print(data.head())
  out.write(frame)
data['frame']=frameid
data['lx']=lx
data['ty']=ty
data['rx']=rx
data['by']=by
data['id']=uid
data.to_csv("video_track.csv")
cap.release()
out.release()
