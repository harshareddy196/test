# -*- coding: utf-8 -*-
"""
Created on Thu Jul 26 14:14:51 2018

@author: ABHISHEK
"""

import xml.etree.ElementTree as ET

def findOccurences(s, ch):
    return [i for i, letter in enumerate(s) if letter == ch or letter == "\n"]

def get_doubles(alist):
    return list(zip(alist, alist[1:]))

def adjust_indices(alist):
    # first as it is
    adj_list = [alist[0][:]]
    for a,b in alist[1:]:
        adj_list.append((a+1, b))
    return adj_list

def calculate_width_height(word, coords):
    ###print "sentence got:", word, len(word)
    confidence = calculate_confidence(word,coords)
    if len(word) == 1:
        # ##print word[0], coords[0]
        return {"word":word.replace('"','').replace("'",''), "width":float(coords[0][1]['r'])-float(coords[0][1]['l']), "height":float(coords[0][1]['b'])-float(coords[0][1]['t']),
        "top":float(coords[0][1]['t']), "left":float(coords[0][1]['l']),
        "bottom":float(coords[0][1]['b']), "right":float(coords[0][1]['r']),"confidence":float(confidence)}

    else:
        # ##print word[0], coords[0]
        # ##print word[-1], coords[-1]
        # return (word, float(coords[-1][1]['r'])-float(coords[0][1]['l']), float(coords[-1][1]['b'])-float(coords[0][1]['t']))
        if coords[-1][0] == "\n":
            left = float(min([int(coord[1]['l']) for coord in coords[:-1]]))
            right = float(max([int(coord[1]['r']) for coord in coords[:-1]]))
            top = float(min([int(coord[1]['t']) for coord in coords[:-1]]))
            bottom = float(max([int(coord[1]['b']) for coord in coords[:-1]]))

            width = float(right - left)
            height = float(bottom - top)
        else:
            left = float(min([int(coord[1]['l']) for coord in coords]))
            right = float(max([int(coord[1]['r']) for coord in coords]))
            top = float(min([int(coord[1]['t']) for coord in coords]))
            bottom = float(max([int(coord[1]['b']) for coord in coords]))

            width = float(right - left)
            height = float(bottom - top)

        return {"word": word.replace('"', '').replace("'", ''), "width": width, "height": height,
                "top": top, "left": left,
                "bottom": bottom, "right": right, "confidence": float(confidence)}

def resize(result,resize_factor):
    for i in result:
        i["width"] = int(i["width"] * resize_factor)
        i["height"] = int(i["height"] * resize_factor)
        i["top"] = int(i["top"] * resize_factor)
        i["left"] = int(i["left"] * resize_factor)
        i["bottom"] = int(i["bottom"] * resize_factor)
        i["right"] = int(i["right"] * resize_factor)
    return result

def calculate_confidence(word,coords):
    confidence = 0
    if len(word)==1:
        if 'suspicious' not in coords[0][1]:
            confidence = 100
        else:
            confidence = 0
    else:
        count_suspicious=0
        for i in range(len(word)):
            if 'suspicious' in coords[i][1]:
                count_suspicious+=1
        if count_suspicious:
            confidence = ((len(word) - count_suspicious)/len(word)) * 100
        else:
            confidence = 100

    return round(confidence,2)

def isTab(child):
    if ('isTab' in child.attrib):
        if child.attrib['isTab'] == '1':
            return True
    return False
def convert_to_json(xml,std_width=670):
    # load and parse the file
    tree = ET.fromstring(xml)
    # maintain the list
    result = []
    results = []
    pages = []
    width = 1
    resize_factor = 1
    # parse over the tree
    dpi_page = []
    for element in tree.iter():
        if element.tag == '{http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml}page':
            result = resize(result,resize_factor)
            # ##print(result)
            width = element.attrib["width"]
            try:
                dpi_page.append(int(element.attrib['resolution']))
            except:
                dpi_page.append(0)
            resize_factor = float(std_width)/float(width)
            results.append(result)
            result = []
        if element.tag == '{http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml}formatting':
            children = element.getchildren()
            coords = []
            sentence = ''
            for child in children:
                if child.tag == "{http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml}charParams":
                    if child.text:
                        if child.text != '\n':
                            #print ("*&"*20)
                            #print ("HEREEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEee")
                            if ('isTab' in child.attrib):
                                #print ("TAB "*50)
                                if child.attrib['isTab'] == '1':
                                    sentence += ' '
                                else:
                                    sentence += child.text
                            else:
                                sentence += child.text
                            #print ("&"*50)
                            #print ("APPENDING THE COORDS OF")
                            #print (child.text)
                            #print (child.attrib)
                            #print ("&"*50)
                            coords.append((child.text, child.attrib))
            #print ("*"*50)
            #print ("sentence is \n\n\n\n\n", sentence)
            #print ("*"*50)
            if len(sentence.split()) > 1:
                space_indices = findOccurences(sentence, " ")
                space_indices_added = [0]+space_indices+[len(sentence)]
                for a,b in adjust_indices(get_doubles(space_indices_added)):
                    if sentence[a:b]:
                        #print ("#"*50)
                        #print (sentence[a:b])
                        #print (coords[a:b])
                        #print ("#"*50)
                        result.append(calculate_width_height(sentence[a:b], coords[a:b]))
            else:
                if sentence:
                    result.append(calculate_width_height(sentence, coords))

    result = resize(result,resize_factor)
    # ##print(result)
    results.append(result.copy())
    return results[1:], dpi_page
