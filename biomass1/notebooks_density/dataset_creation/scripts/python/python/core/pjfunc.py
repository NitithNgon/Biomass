import numpy as np
import laspy
import matplotlib.pyplot as plt
import shutil
import os

def writeLas(filename,data,scale = 10**-6):
    
    # Handle empty data
    if len(data) == 0:
        raise ValueError("Cannot write LAS file with empty data array (0 points)")
   
    header = laspy.LasHeader(point_format=6)
    header.offsets = np.min(data, axis=0)
    header.scales = np.array([scale, scale, scale])

    with laspy.open(filename, mode="w", header=header) as writer:
        point_record = laspy.ScaleAwarePointRecord.zeros(data.shape[0], header=header)
        point_record.x = data[:, 0]
        point_record.y = data[:, 1]
        point_record.z = data[:, 2]
        writer.write_points(point_record)


def readLas(filename):
    with laspy.open(filename) as fh:
        print('Points from Header:', fh.header.point_count)
        las = fh.read()
        def getXYZ(las):
            x = las.X
            y = las.Y
            z = las.Z
            scales = las.header.scales
            offset = las.header.offset
            x = np.reshape(offset[0]+(x*scales[0]),(-1,1))
            y = np.reshape(offset[1]+(y*scales[1]),(-1,1))
            z = np.reshape(offset[2]+(z*scales[2]),(-1,1))
            
            return np.concatenate((x,y,z),axis = 1)

        dat = getXYZ(las)
    return dat


def readODM(filename):
    x = []
    y = []
    z = []
    with open(filename,"r") as f:
        reader = f.readlines()
        for i in reader:
            k = i.split()
            x.append(float(k[2]))
            y.append(float(k[3]))
            z.append(float(k[4]))
    x = np.array(x)
    y = np.array(y)
    z = np.array(z)
    return x,y,z


def circleFit(X):
    import numpy as np
     # Circular Fitting
    D = X[:,0]**2+X[:,1]**2
    X0 = X[:,0]
    X1 = X[:,1]
    X2 = X[:,0]*0+1.
    G = np.vstack((X0,X1,X2))
    G = G.TP
    
    from scipy.linalg import solve
    A = np.matmul(G.T,G)
    B = np.matmul(G.T,D)

    condition_number = np.linalg.cond(A)
    if condition_number > 1e12:
        raise ValueError(
            f"Matrix A is near-singular (condition number: {condition_number:.2e}). "
            "Circle fitting cannot proceed."
        )

    res = solve(A,B)
    xc = res[0]/2
    yc = res[1]/2
    r2 = res[2]+xc**2+yc**2
    r = np.sqrt(r2)
    return xc,yc,r

def filter_xyz(X,minV,maxV,col):
    import numpy as np
    K = np.logical_and(X[:,col]>minV, X[:,col]<maxV)
    G = np.nonzero(K)
    X_new = X[G,:]
    return X_new[0]


def compressDBH(dat):
    n = len(dat)
    currT = 1
    meanCS = []
    rangeCS = []
    dbh = []
    sdCS = []
    #rangeTree = np.zeros(shape = 87)

    for i in range(n):
        #print(dat[i,0]," vs ",currT)
        if dat[i,0] != currT:
            if len(dbh)>0:
                dbh = np.array(dbh)
                meanCS.append(np.mean(dbh))
                sdCS.append(np.std(dbh))
                rangeCS.append(np.max(dbh)-np.min(dbh))
                dbh = []
            #print("Tree {} mean = {} sd = {}".format(currT,meanCS[-1],sdCS[-1]))
            else:
                meanCS.append(None)
                sdCS.append(None)
                rangeCS.append(None)

            currT += 1
            
            
        if dat[i,2] == 0:
            if dat[i,5] != None:
                dbh.append(dat[i,5])
    if len(dbh)>0:
        dbh = np.array(dbh)
        meanCS.append(np.mean(dbh))
        sdCS.append(np.std(dbh))
        rangeCS.append(np.max(dbh)-np.min(dbh))
        dbh = []
    else:
        meanCS.append(None)
        sdCS.append(None)
        rangeCS.append(None)


    def getPerr(sdcs,mcs):
        if sdcs != None:
            return sdcs/mcs*100
        else:
            return sdcs
    getPerr = np.vectorize(getPerr) 

    def getCI(sdcs):
        if sdcs != None:
            return 1.96*sdcs/np.sqrt(3)
        else:
            return sdcs
    getCI = np.vectorize(getCI) 

    def getPerr2(ci,mcs):
        if mcs != None:
            return ci/mcs*100
        else:
            return ci
    getPerr2 = np.vectorize(getPerr2) 

    #print(meanCS)
    #print(sdCS)

    perror = getPerr(np.array(sdCS),np.array(meanCS))
    #print(perror)
    #perror = np.array(sdCS)/np.array(meanCS)*100 # SD/mean*100
    CI = getCI(np.array(sdCS))
    #print(CI)
    #CI = 1.96*np.array(sdCS)/np.sqrt(3) #95% confidence interval
    perror2 = getPerr2(CI,np.array(meanCS))
    #perror2 = CI/np.array(meanCS)*100

    compressDat = np.zeros(shape = (currT,2))
    compressDat[:,0] = meanCS
    compressDat[:,1] = CI
    np.savetxt("compressed_dat.csv",compressDat,delimiter = ",")

    cwd = os.getcwd()
    rwd = os.path.join(cwd,"res")
    shutil.move(os.path.join(cwd,"compressed_dat.csv"),os.path.join(rwd,"compressed_dat.csv"))
   
    return compressDat
