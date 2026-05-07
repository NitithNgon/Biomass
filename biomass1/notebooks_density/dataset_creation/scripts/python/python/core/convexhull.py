import numpy as np
import matplotlib.pyplot as plt

def convexHull(x,y):
    N = len(x)
    def project(x1,x2,x3):
        yt = x1[1]+(x2[1]-x1[1])/(x2[0]-x1[0])*(x3[0]-x1[0])
        return yt
    X = np.zeros(shape = (N,3))
    X[:,0] = x
    X[:,1] = y
    X[:,2] = np.array(range(N))
    
    # Convex Hull
    xorder = np.argsort(x)
    x = x[xorder]
    y = y[xorder]
    X = X[xorder]

    L = [0,1]
    for k in range(N):
        for i in range(2,len(X)):
            deterS = [L[-2],L[-1],i]
            if X[deterS[1]][0]!=X[deterS[0]][0]:
                yt = project(X[deterS[0]], X[deterS[1]], X[deterS[2]])
                if yt>X[deterS[2]][1]:
                    L.append(i)
                else:
                    L.pop(-1)
                    L.append(i)
            else:
                if X[deterS[1]][1]>X[deterS[2]][1]:
                    L.append(i)
                else:
                    L.pop(-1)
                    L.append(i)

        if len(L)==len(X):
            break
        else:
            X = X[L]
            L = [0,1]
        
    BestXUp = X
    
    x = np.flip(x)
    y = np.flip(y)
    X = np.zeros(shape = (N,3))
    X[:,0] = x
    X[:,1] = y
    X[:,2] = np.array(range(N))
    
    
    L = [0,1]
    for k in range(N):
        for i in range(2,len(X)):
            deterS = [L[-2],L[-1],i]
            if X[deterS[1]][0]!=X[deterS[0]][0]:
                yt = project(X[deterS[0]], X[deterS[1]], X[deterS[2]])
                if yt>X[deterS[2]][1]:
                    L.pop(-1)
                    L.append(i)
                else:
                    L.append(i)
            else:
                if X[deterS[1]][1]>X[deterS[2]][1]:
                    L.pop(-1)
                    L.append(i)
                else:
                    L.append(i)
    
        if len(L)==len(X):
            break
        else:
            X = X[L]
            L = [0,1]
    
        
    BestXDown = X
    
    bX = np.concatenate((BestXUp, BestXDown[1:]),axis = 0)
    return bX


def getInsidePoints(targetPoints,bX):
    conKeep = np.zeros(shape = len(targetPoints),dtype = int)
    import time
    t0 = time.time()
    print("Loop number = {}".format(len(bX)-1))
    for i in range(len(bX)-1):
        t1 = time.time()
        if bX[i+1,1]>bX[i,1]:
            x1 = bX[i,0]
            x2 = bX[i+1,0]
            
            y1 = bX[i,1]
            y2 = bX[i+1,1]
        
        elif y2 == y1:
            x1 = bX[i,0]
            x2 = bX[i+1,0]
            
            y1 = bX[i,1]
            y2 = bX[i+1,1]
            mx = min(x1,x2)
            cond1 = targetPoints[:,0]<mx
            cond2 = targetPoints[:,1]==y1
            cond = np.logical_and(cond1,cond2)
            conKeep += cond
            break
        
        else:
            x1 = bX[i+1,0]
            x2 = bX[i,0]    
            y1 = bX[i+1,1]
            y2 = bX[i,1]
        
        step0 = time.time()
        dx = x2-x1
        dy = y2-y1
        step1 = time.time()
        
        band = np.logical_and(targetPoints[:,1]>=y1,targetPoints[:,1]<y2)
        step2 = time.time()

        borderX = x1+(dx)/(dy)*(targetPoints[:,1]-y1)
        step3 = time.time()

        cond1 = targetPoints[:,0]<borderX
        step4 = time.time()

        cond = np.logical_and(band,cond1)
        stepF = time.time()

        conKeep +=cond
        t2 = time.time()
    #conKeep = conKeep
    temp1 = conKeep
    conKeep = conKeep%2
    conKeep = conKeep.astype(bool)
    return conKeep


def getInsidePoints2(points,P):
    N = len(P)
    pLabel = np.zeros(shape = points.shape[0],dtype = int)

    for i in range(N-1):
        p1 = P[i]
        p2 = P[i+1]

        diffPoints = points-p1
        diffPoly = p2-p1
        crossVector = diffPoints[:,0]*diffPoly[1]-diffPoints[:,1]*diffPoly[0]
        criteriaVector = crossVector<0
        pLabel += criteriaVector
    return (pLabel == N-1)