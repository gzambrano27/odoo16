# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import os
import tempfile
import shutil
from odoo import _
import logging
_logger = logging.getLogger(__name__)


class FileManager(object):
    
    def __init__(self):
        pass
    
    def log(self,obj):
        try:        
            _logger.warning("%s",(obj,))
        except Exception as e:
            print(str(e))
        return obj
   
    def encode64(self,data):
        return base64.b64encode(data)    
    
    def decode64(self,data):
        return base64.b64decode(data)   

    def copy(self,file_name,to_folder,remove=False):
        try:
            self.log(_("MOVING FILE %s TO %s...") % (file_name,to_folder))
            shutil.copy(file_name, to_folder+"/")
            if remove:
                self.remove(file_name)
        except Exception as e:
            self.log(e)        
    
    def copyfile(self,original,target):
        try:
            self.log(_("COPY FILE %s TO %s...") % (original,target))
            shutil.copyfile(original, target)
        except Exception as e:
            self.log(e) 
            
    def remove(self,filename):
        try:
            os.remove(filename)
        except Exception as e:
            self.log(e)         
    
    def exist(self,filename):
        try:
            return os.path.exists(filename)
        except Exception as e:
            self.log(e)
            return False
                  
    def create(self,ext):
        f = tempfile.NamedTemporaryFile(delete=False, suffix="."+ext)
        f.close()
        return f.name

    def get_binary(self,filename):
        data=False
        with open(filename, mode='rb') as file:
            fileContent = file.read()
            data = fileContent
        return data
    
    def get_binary_encodebase64(self,filename):
        data=self.get_binary(filename)
        if data:
            return self.encode64(data)
        return data

    def get_binary_decodebase64(self,filename):
        data=self.get_binary(filename)
        if data:
            return self.decode64(data)
        return data 
    
    def write(self,filename,str_data,modeWrite="wb"):
        with open(filename, mode=modeWrite) as file:
            file.write(str_data)
        return str_data
    
    def join(self,path, *p):
        return os.path.join(path,*p)
    
    def get_module_src(self,static_path=True,module=None):
        separator=os.sep
        localpath=os.path.dirname(__file__)
        localpath=localpath.replace(separator+"tools","")  
        path=self.join(localpath)
        if static_path: 
            path=self.join(path,"static","src")
        if module is None:
            return path
        fullpath=path.replace(module,"{}")
        fullpath=fullpath.format(module,)
        return self.join(fullpath)
    
    def create_path(self,path):
        if(not os.path.exists(path)):
            os.makedirs(path)
            return True
        return False
    
    def get_ext(self,filename):
        file_parts=filename.split('.')
        if file_parts:
            if file_parts.__len__()>1:
                return file_parts[1]
        return ""
    
    def list_files(self,path,ext=False):
        files = []
        for item in os.listdir(path):
            item_full_path = os.path.join(path, item)
            if not os.path.isdir(item_full_path):
                if ext:
                    if ext.lower() in item.lower():
                        files.append((item,item_full_path))
        return files
    
    def list_folder(self,path,recursive=True):
        l=[]
        for item in os.listdir(path):
            item_full_path = os.path.join(path, item)
            if os.path.isdir(item_full_path):
                l.append((item,item_full_path))
            if recursive:
                l=l+self.list_folder(item_full_path,recursive=recursive)
        return l
    
    def get_path_file(self,filename):
        dir_path = os.path.dirname(os.path.realpath(filename))
        return dir_path
    