# import string
from odoo import models, fields, api, tools, _
import json
import requests
import json
# from PIL import Image
from io import BytesIO
from odoo.exceptions import UserError
# import cv2
import urllib.request
# import numpy as np
# from urllib.request import urlopen
import base64

class long_token(models.Model):
    _name = 'insta.credential'

    long_token = fields.Char("Long Access Token")
    insta_username = fields.Char("Instagram User Name")
    insta_acc_id = fields.Char("Insta Account ID")

class cret_insta(models.Model):
    _name = 'get.insta'

    token = fields.Char("Acess Token")
    # long_token = fields.Char("Long Access Token")
    # insta_acc_id = fields.Char("Insta Account ID")
    fb_page_id = fields.Char("FB Page ID")
    client_id = fields.Char("APP Client ID")
    clinet_sec_id = fields.Char("Client Secret ID")
    # insta_username = fields.Char("Instagram User Name")
    def generate_token(self):
        sh_token = str(self.token)
        fb_pg_id = str(self.fb_page_id)
        app_id = str(self.client_id)
        cln_sec_id = str(self.clinet_sec_id)
        # ins_username = str(self.insta_username)
        
        #generate long access token
        url = f"https://graph.facebook.com/v14.0/oauth/access_token?grant_type=fb_exchange_token&client_id={app_id}&client_secret={cln_sec_id}&fb_exchange_token={sh_token}"
        payload={}
        headers = {}
        response = requests.request("GET", url, headers=headers, data=payload).json()
        
        lo_tko = response['access_token']
        #generate instagram account ID

        url_ins_id = f"https://graph.facebook.com/v14.0/{fb_pg_id}?access_token={lo_tko}&fields=instagram_business_account"
        payload={}
        headers = {}
        response_id = requests.request("GET", url_ins_id, headers=headers, data=payload).json()
        obj = self.env['insta.credential']
        obj.create({
                'insta_acc_id' :response_id['instagram_business_account']['id'],
                'long_token': lo_tko,
                
                })
        

        
class instacomment(models.Model):
    _name="insta.comment"       
    post_id = fields.Many2one("insta.post",string="Post ID")
    comment = fields.Char("Comments")
    com_id = fields.Char("Comment ID")
    username = fields.Char("User Name")
    reply_comment = fields.Char("Replay Comments")
    response_id = fields.Char("Response ID")
    save_comments = fields.Char("Reply")
    
    def com_reply(self):
        c_id = self.com_id
        
        obj = self.env['insta.comment']
        ids =  self._context['comid']
        text = self._context['text']
        
        
        url = f"https://graph.facebook.com/v14.0/{ids}/replies?message={text}&access_token=EAASv5tDfVoEBAHEDrWFpmleBOxIO7J5fjRiMZAbHfZASZCVWQU3XiNjOtsDnQhMgszSLyUMtzWJrCczaleTljZAdaQ8sK4I7ZB9ZCySZAPZACsyjYQE2AsW2tKc5fU4ibaSiGcptAs0BVQ3zAQ3Avc4MJIXzDoa7q4qmtjMue5UK3Uy1KZAWgMoiIONOvRcHZCEaMZD"
        payload={}
        headers = {}
        response = requests.request("POST", url, headers=headers, data=payload).json()
        
        
        obj.create({
            "response_id" : response['id'], 
             "save_comments": text
             }) 




    def get_Comment(self):
        obje = self.env['insta.credential']
        da = obje.search([])
        for i in da:
            token = i.long_token
            acc_id = i.insta_acc_id 
        url = f"https://graph.facebook.com/v14.0/{acc_id}/media?fields=id,caption,media_type,media_url,permalink&access_token={token}"
        payload={}
        headers = {}
        obj = self.env['insta.post']
        c_obj = self.env['insta.comment']
        response = requests.request("GET", url, headers=headers, data=payload)

        json_data = json.dumps(response.text)
        data = json.loads(response.text)
        for d in data['data']:
            pid = obj.search([('postid','=',d['id'])])
            url = f"https://graph.facebook.com/v14.0/{pid.postid}/comments?fields=like_count,replies,username,text&access_token={token}"
            payload={}
            headers = {}
            response = requests.request("GET", url, headers=headers, data=payload).json()
            for i in response['data']:
                already = c_obj.search([('com_id','=',i['id'])])
                if not already:
                    c_obj.create({
                    
                    'post_id' : pid.id,
                    'comment' : i['text'],
                    'com_id' : i['id'],
                    "username" : i['username']
                })
        


class instamodel(models.Model):
    _name = 'insta.post'
    
    postid = fields.Char("Post ID")
    postimage = fields.Binary(string="Image", attachment=False, stored=True)
    caption = fields.Char("Caption")
    permlink = fields.Char("Link")
    starttime = fields.Float("Start Time") 
    comment = fields.One2many("insta.comment", "post_id", string="Comments")
    media_type = fields.Char("Media Type")
   
    

    
    def getPost(self):
        
        obje = self.env['insta.credential']
        da = obje.search([])
        for i in da:
            token = i.long_token
            acc_id = i.insta_acc_id 
        
        url = f"https://graph.facebook.com/v14.0/{acc_id}/media?fields=id,caption,media_type,media_url,permalink&access_token={token}"
        payload={}
        headers = {}
        obj = self.env['insta.post']
        response = requests.request("GET", url, headers=headers, data=payload)

        json_data = json.dumps(response.text)
        data = json.loads(response.text)
        
        for d in data['data']:
            
            im_url = d['media_url']
            data = base64.b64encode(requests.get(im_url.strip()).content).replace(b"\n", b"")

                
            already=obj.search([('postid','=',d['id'])])
            if not already:
                obj.create({
                    'postid':d['id'],
                    'caption':d['caption'],
                    'permlink': d['permalink'],
                    'postimage' : data,
                    'media_type' : d['media_type']
                    
                })
        
          


    
# class helpdesk(models.Model):
#     _inherit = 'helpdesk.ticket'
#     # commeent_id =fields.Char("Comment ID")
#     post_id = fields.Many2one('insta.post','Post ID')

    
#     def comment(self):
#         #check customer
#         def getcustomer(username):
#             customer_obj=self.env['res.partner']
#             check_customer=customer_obj.search([('name','=',username)])
            
#             if check_customer:
#                 return check_customer.id
#             else:
#                 created_c=customer_obj.create({'name':username})
#                 return created_c.id
#         #check comment
#         # def comment_check(comment):
#         #     comment_obj=self.env['helpdesk.ticket']
#         #     check_comment=comment_obj.search([('commeent_id','=',comment)])
#         #     if check_comment:
#         #         check_comment.id
#         #     else:
#         #         created_comment =  comment_obj.create({'commeent_id':comment})
#         #         return created_comment.id

#         obj = self.env['insta.post']
    
#         obj_desk=self.env['helpdesk.ticket']
#         all_posts=obj.search([])
#         for i in all_posts:
#             url = f"https://graph.facebook.com/v14.0/{i.postid}/comments?fields=like_count,replies,username,text&access_token=EAASv5tDfVoEBAOKkR3ImFUI5t9LZADex9hMZBn125ZAjZBfCWvJW9d5reOhvGbgeb2ZBSMRjKIrLxZBjH04ZC7L5SThdhRIwnIdmdIcNvthjFugZBKVzNhWEZAYZAy7uMwgLHYEK3PQ954CVvXXXPe72x1QeR2tdp6mv7J7H2BbgCSZAqnKzTWjhcogcbVNQYUdvT8ZD"
#             payload={}
#             headers = {}

#             response = requests.request("GET", url, headers=headers, data=payload).json()
#             if 'data' in response.keys():
#                 for j in response['data']:
                    
#                     if 'text' in j.keys():
                       
#                         ticket_create=obj_desk.create({
#                             'name': j['text'],
#                             'post_id': i.id,
#                             'partner_id':getcustomer(j["username"]),
#                             'team_id':3
#                             })
            
                        






