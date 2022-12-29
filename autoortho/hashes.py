import os
import json
import glob
import sys
from PIL import Image
import imagehash
from annoy import AnnoyIndex
import numpy as np
from jinja2 import Template

def get_img_hashes(img):
    #img = img.reduce(16)
    #phash_str = str(iw_hash.phash(img, order = 'RGB'))
    phash_str = str(imagehash.phash(img))
    chash_str = str(imagehash.colorhash(img, 6))
    return phash_str, chash_str

def get_hash_array(img, hashtype):
    
    phash = imagehash.phash(img)
    chash = imagehash.colorhash(img, 6)
    
    if hashtype == "chash":
        hash_array = chash.hash.astype('int').flatten()
    elif hashtype == "phash":
        hash_array = phash.hash.astype('int').flatten()
    elif hashtype == "combo":
        chash_array = chash.hash.astype('int').flatten()
        phash_array = phash.hash.astype('int').flatten()
        hash_array = np.concatenate((phash_array, chash_array))

    return hash_array
    

def makehashes(imgdir):
    
    img_dict = {}
    if os.path.exists("imghashes.json"):
        with open("imghashes.json", "r") as h:
            img_dict = json.loads(h.read())



    imgs = glob.glob(f"{imgdir}/**/*", recursive=True)

    count = 0
    for img in imgs:
        if os.path.splitext(img)[1] not in ['.jpg', '.jpeg', '.dds']:
            continue

        if img in img_dict:
            continue

        print(img)
        #in_img = Image.open(os.path.join(imgdir, img))
        in_img = Image.open(img)
        
        #in_img = in_img.reduce(4)
        in_img = in_img.reduce(16)


        phash, chash = get_img_hashes(in_img)
        img_dict[img] = {'phash':phash, 'chash':chash}

        count += 1

        if count % 10 == 0:
            print("Saving checkpoint ...")
            with open("imghashes.json", "w") as h:
                h.write(json.dumps(img_dict))

    print(f"Processed {count} images.")
    with open("imghashes.json", "w") as h:
        h.write(json.dumps(img_dict))

    return img_dict



def makeindex(img_dict, hashtype="chash"):
    vector_len = 0
    id_to_vec = {}

    imglist = []
    for img in img_dict.keys():
        imglist.append(img)

    if os.path.exists('imghash.tree'):
        #phash_str = img_dict.get(imglist[0]).get('phash')
        #phash = imagehash.hex_to_hash(phash_str)
        #hash_array = phash.hash.astype('int').flatten()
        #f = hash_array.shape[0]
        #f = 64
        if hashtype == "combo":
            f = 106
        elif hashtype == "chash":
            f = 84
        else:
            f = 64
        dist_function = "hamming"
        t = AnnoyIndex(f, dist_function)
        t.load('imghash.tree')
    else:
        for count,img in enumerate(imglist):
            phash_str = img_dict.get(img).get('phash')
            chash_str = img_dict.get(img).get('chash')
            
            phash = imagehash.hex_to_hash(phash_str)
            chash = imagehash.hex_to_flathash(chash_str, hashsize=6)
            
            if hashtype == "chash":
                hash_array = chash.hash.astype('int').flatten()
            elif hashtype == "phash":
                hash_array = phash.hash.astype('int').flatten()
            elif hashtype == "combo":
                chash_array = chash.hash.astype('int').flatten()
                phash_array = phash.hash.astype('int').flatten()
                hash_array = np.concatenate((phash_array, chash_array))

            #print(hash_array)
            vector_len = hash_array.shape[0]
            id_to_vec[count] = hash_array

        f = vector_len
        dist_function = "hamming"
        t = AnnoyIndex(f, dist_function)

        for key, value in id_to_vec.items():
            t.add_item(key, value)

        num_trees = 200
        t.build(num_trees)
        t.save('imghash.tree')

    return t, imglist

def find_hash(imghash_t, hashtree, imglist, img_dict, hashtype="chash", threshold=20, secondary=None):

    phash_str = imghash_t[0]
    chash_str = imghash_t[1]

    chash = imagehash.hex_to_flathash(chash_str, hashsize=6)
    phash = imagehash.hex_to_hash(phash_str)

    if hashtype == "chash":
        hash_array = chash.hash.astype('int').flatten()
    elif hashtype == "phash":
        hash_array = phash.hash.astype('int').flatten()
    elif hashtype == "combo":
        chash_array = chash.hash.astype('int').flatten()
        phash_array = phash.hash.astype('int').flatten()
        hash_array = np.concatenate((phash_array, chash_array))
    
    if secondary == "chash":
        orig_2nd_hash_str = chash_str
        orig_2nd_hash = imagehash.hex_to_flathash(orig_2nd_hash_str, hashsize=6)
    elif secondary == "phash":
        orig_2nd_hash_str = phash_str
        orig_2nd_hash = imagehash.hex_to_hash(orig_2nd_hash_str)

    num_neighbors = 9
    neighbors = hashtree.get_nns_by_vector(hash_array, num_neighbors, include_distances=True)

    #matches = {}
    close_matches = []
    matchcount = 0
    for idx in range(num_neighbors):
        
        img = imglist[neighbors[0][idx]]
        distance = neighbors[1][idx]

        #if img == imgpath:
        #    continue
        
        if secondary == "chash":
            chash_str = img_dict.get(img).get('chash')
            second_hash = imagehash.hex_to_flathash(chash_str, hashsize=6)
        elif secondary == "phash":
            phash_str = img_dict.get(img).get('phash')
            second_hash = imagehash.hex_to_hash(phash_str)

        if distance < threshold:
            if secondary:
                close_matches.append(((orig_2nd_hash - second_hash), distance, img))
            else:
            #close_matches.append(((orig_chash - chash), img, distance))
                close_matches.append((distance, img))
            matchcount += 1
    

    if close_matches:
        #print(f"Matches for {imgpath} ....")
        close_matches.sort()
        #matches[imgpath] = close_matches

    
    #for r in close_matches:
    #    print(f"  {r}")
    #print(f"Total close matches {matchcount}")

    return close_matches


def find_similar(imgpath, hashtree, imglist, hashtype="chash", threshold=20, secondary=None):

    in_img = Image.open(imgpath)
    in_img = in_img.reduce(16)
    hash_array = get_hash_array(in_img, hashtype)
    
    if secondary == "chash":
        orig_2nd_hash_str = img_dict.get(imgpath).get('chash')
        orig_2nd_hash = imagehash.hex_to_flathash(orig_2nd_hash_str, hashsize=6)
    elif secondary == "phash":
        orig_2nd_hash_str = img_dict.get(imgpath).get('phash')
        orig_2nd_hash = imagehash.hex_to_hash(orig_2nd_hash_str)

    num_neighbors = 9
    neighbors = hashtree.get_nns_by_vector(hash_array, num_neighbors, include_distances=True)

    #matches = {}
    close_matches = []
    matchcount = 0
    for idx in range(num_neighbors):
        
        img = imglist[neighbors[0][idx]]
        distance = neighbors[1][idx]

        if img == imgpath:
            continue
        
        if secondary == "chash":
            chash_str = img_dict.get(img).get('chash')
            second_hash = imagehash.hex_to_flathash(chash_str, hashsize=6)
        elif secondary == "phash":
            phash_str = img_dict.get(img).get('phash')
            second_hash = imagehash.hex_to_hash(phash_str)

        if distance < threshold:
            if secondary:
                close_matches.append(((orig_2nd_hash - second_hash), distance, img))
            else:
            #close_matches.append(((orig_chash - chash), img, distance))
                close_matches.append((distance, img))
            matchcount += 1
    

    if close_matches:
        print(f"Matches for {imgpath} ....")
        close_matches.sort()
        #matches[imgpath] = close_matches

    
    for r in close_matches:
        print(f"  {r}")


    print(f"Total close matches {matchcount}")

    return close_matches


def display(inimg, matches):

    with open("similar.html", "r") as h:
        template = Template(h.read())

    converted_matches = []
    
    for m in matches:
        mpath = m[-1]
        
        if os.path.splitext(mpath)[1] not in ['.dds']:
            converted_matches.append(m)
            continue

        mname = os.path.basename(mpath)
        mimg = Image.open(mpath)
        #mimg.convert('jpg')
        mimg.save(f"output/{mname}.png")

        if len(m) == 2:
            new_match = (
                m[0], 
                f"output/{mname}.png"
            )
        else:
            new_match = (
                m[0], 
                m[1], 
                f"output/{mname}.png"
            )
        
        converted_matches.append(new_match)


    print(converted_matches)

    outhtml = template.render(
        inimg = inimg,
        matches = converted_matches
    )

    with open(f"out.html", "w") as h:
        h.write(outhtml)


if __name__ == "__main__":
    imgdir = sys.argv[1]
    imgpath = sys.argv[2]

    hashtype = "phash"
    img_dict = makehashes(imgdir)
    hashtree, imglist = makeindex(img_dict, hashtype)

    matches = find_similar(imgpath, hashtree, imglist, hashtype, secondary="chash")
    display(imgpath, matches)
