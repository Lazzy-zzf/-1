# -*- coding: utf-8 -*-
"""
Created on Mon Sep  2 15:07:05 2019

@author: 123
"""


import urllib.request
import urllib.parse

from bs4 import BeautifulSoup 
from lxml import etree
#import xml.etree.ElementTree as ET

import json
import os
import time
import random
import signal


class NovelSpider():    #"https://webnovel.online/zhu-xian/chapter-1"
    """
    
    """
    def __init__(self, novel_name, novel_url: str=''):
        self.novel_name = novel_name    #不同实例对应不同小说，生成不同小说文件
        self.url_start = novel_url
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36'
        }
        
        
    def parse_url(self, url, data=None, headers=None):  #data参数必须为byte类型
        if not headers:
            headers = self.headers
        req = urllib.request.Request(url=url, data=data, headers=headers)
        
        for i in range(10):     #尝试最多10次
            try:
                response = urllib.request.urlopen(req, timeout=5)
                return response.read().decode('utf-8')
            except urllib.URLError as err:
                print(err)
                print('NetworkError! Try it again.')
                time.sleep(random.random())     #暂停0~1s
        
        print('times run out!')
        return None
        
        
    def count_node_str(self, node)->int:
        """
        输入beautifulsoup的tag节点的第一个子节点，如：bsobj.contents[0]。注：beautifulsoup中字符串和tag都是节点
        输出该tag节点的字符串长度总和
        使用beautifulsoup库
        求取根节点下所有字符串长度也可采用如下代码：
        count = 0
        for i in bsobj1.contents[0].next_elements:      #beautifulsoup类型的next_element为None
            if isinstance(i,str):
                count += len(repr(i))
        """
        if node == None:
            return 0
        if isinstance(node, str):
            mstring = str(node)
            mstring = mstring.replace(' ', '')
            mstring = mstring.replace('\n', '')     #过滤空格和换行符
            return len(mstring) + self.count_node_str(node.next_sibling)
        else:
            if node.contents == []:
                return self.count_node_str(node.next_sibling) 
            else:
                return self.count_node_str(node.next_sibling) + self.count_node_str(node.contents[0])
        
        """
        输入lxml的element节点，返回该element节点及其子孙节点的字符串长度总和
        使用lxml库
        """
        """substitution
        count = 0
        for i in node.itertext():
            i = i.replace(' ', '')
            i = i.replace('\n', '')        #过滤空格和换行符
            count += len(i)
        return count   
        """
    
    def get_chapter_content(self, chapter_url, chapter_name):
        """start: 17:00 ~ 23:49
        输入目标网址，输出包含其主要内容文字的字符串
        使用bs4(beautifulsoup)库
        试验心得：对于博客、小说、问答类网页适用性较好。通过调整阈值thread_len可改变截取的正文范围
        """
        html_str = self.parse_url(chapter_url)
        if not html_str:
            print(f'{chapter_name}章节网址访问出错！')
            return ''
        
        try:
            """ #bug：标记文档中空格不可删去！
            html_str = html_str.replace(' ','')         #注：replace返回值才有效！
            html_str = html_str.replace('\n','')       #过滤html文件中的空格和换行符
            """
            bsobj = BeautifulSoup(html_str)
            total_len = self.count_node_str(bsobj.contents[0])
            thread_len = total_len // 2     #计算阈值
    #        print(thread_len)
            
            checking_node = bsobj             #查找正文所在父节点
            flag = 1
            while flag:
                flag = 0
                for node in checking_node.children:
                    if isinstance(node,str):    #跳过bs4.element.Doctype类型子节点
                        node_len = len(repr(node))
                    elif not node.contents == []:
                        node_len = self.count_node_str(node.contents[0])
                    else:
                        node_len = 0
    #                print(node_len)
                    if node_len >= thread_len:
                        checking_node = node 
                        flag = 1
                        break      
        #try过程可能引发列表索引异常以及对无结果的查找值的属性引用异常
        except (IndexError, AttributeError) as e:
            print(e)
            print(f'{chapter_name}章节内容检索出错！')
            return ''
        
        """使用descendants遍历存在重复读取同一字符串节点bug
        for node in bsobj.descendants:
            total_len += len(repr(node.string))  #此处有一隐患：string只能有效获取该节点的第一个字符串
            print(total_len)
#            print(node.string)
        thread_len = total_len // 2     #计算阈值
        print(f"{thread_len}, {total_len}")
        
        checking_node = bsobj             #查找正文所在父节点
        flag = 1
        while flag:
            flag = 0
            for node in checking_node.children:
                node_len = 0
                if isinstance(node,str):    #跳过bs4.element.Doctype类型子节点
                    node_len = len(repr(node.string))
                else:
                    for i in node.descendants:
                        node_len += len(repr(node.string))
                print(node_len)
                if node_len >= thread_len:
                    checking_node = node 
                    flag = 1
                    break
        """
        
        text = ''
        for node in checking_node.children:
            if not node.string == None:
                mstring = str(node.string)
#                mstring = mstring.replace(' ', '')     #英文中空格必不可少
                mstring = mstring.replace('\n', '')     #过滤文本中的空格和换行符
                text += '    ' + mstring + '\n'   
#        print(text)
        return text
    
    
    def get_chapter_info(self, novel_url):
        """start: 17:05 ~ 19:08
        获取章节信息：章节网址，章节名
        专一性强，适用性较差。对于不同网站，或是跟新版本的网站，本方法需修改查找流程
        使用lxml.etree编写
        小说目录页有两个dl节点，一小一大，后者大而且是每章小说地址信息所在(dl->dd->a)
        """
        html_str = self.parse_url(novel_url)
        if not html_str:
            print('起始网址访问出错！')
            return
        
        base_addr = 'https://www.qktsw.com'         #只适用于www.qktsw.com网站
        try:
            html =etree.HTML(html_str, etree.HTMLParser())
            result = html.xpath('//dl')         #查找流程起始
            result = result[1].findall('dd')
            #错误：此处运行出错！两个dl标签不属于兄弟标签，属于不同树层，不能使用索引方法
    #        result = html.xpath('//dl[2]/dd')      
            for i in result:
                chapter_info = i.find('a')      
                #生成器使用next(generator)方法得到下一个值
                yield [base_addr + chapter_info.get('href'), chapter_info.text]    
                                                 #查找流程终止
        #try过程可能引发列表索引异常以及对无结果的查找值的属性引用异常
        except (IndexError, AttributeError) as e:
            print(e)
            print('Can\'t find the chapter information!')
    
    
    def save_data(self, data_str, file_name='', flag=False):
        """
        flag为真，以写的方式创建文件，否则以追加的方式添加内容
        """
        try:
            if file_name =='':      #扩展save_data函数功能
                file_name = self.novel_name + '.txt'   
                
            if flag:    #创建新文件
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(data_str)
            else:
                with open(file_name, 'a', encoding='utf-8') as f:
                    f.write(data_str)
            return True
        except OSError as e:
            print(e)
            print('文件写入出错！')
            return False
        
        
    def make_gen_file(self, filename):
        """
        从文件中读取每行数据，以生成器的方式输出。
        """
        with open(filename) as fp:
            for line in fp.readlines():
                yield json.loads(line)
        
        
    def try_reload(self):
        """
        进行程序异常终止判定，返回generator生成器
        注：函数存在yield，则会被处理为generator。当运行至return语句时，则会触发迭代终止异常。
        """
        try:
            fp = open('spider-noverl-temp.json', 'r')
            choice = input('存在下载断点，是否继续上次下载(y and Y)？')
            if choice in ['y', 'Y']:
                return self.make_gen_file('spider-noverl-temp.json')
            else:
                fp.close()
                os.remove('spider-noverl-temp.json')
                raise OSError
        except OSError:
            print('\n开始新的下载...')
            self.save_data(data_str='', flag=True)    #建立一个新文件
            return self.get_chapter_info("https://www.qktsw.com/book/57199/")
    
    
    def save_breakpoint(self, data):
        """
        
        """
        with open('spider-noverl-temp1.json', 'w', encoding='utf-8') as fp: 
            for i in data:
                fp.write(json.dumps(i) + '\n')
#                    json.dump(data, fp)
        #防止在同一时间对同一暂存文件重复读写
        if os.path.exists('spider-noverl-temp.json'):
            os.remove('spider-noverl-temp.json')       
        os.rename('spider-noverl-temp1.json', 'spider-noverl-temp.json')
        
    
    def start(self, novel_url: str=''):
        """
        
        """
        signal.signal(signal.SIGINT, signal_handler)
        
        data= self.try_reload()
        
        try:
            failure_list = []
            for chapter_info in data:
                chapter_content = self.get_chapter_content(chapter_info[0], chapter_info[1])
                if chapter_content == '':
                    failure_list.append(chapter_info)
                    key = self.save_data(data_str = '章节缺失\n' + str(chapter_info) + '\n')    #html
                    if not key:
                        raise 
                    continue
                else:
                    key = self.save_data(chapter_info[1] +'\n'+ chapter_content + '\n\n')
                    if not key:
                        raise 
                    print(f'小说{chapter_info[1]}  下载成功！下载继续~')
        except BaseException as e:
            print(e)
            print('程序运行异常，已停止！现进行中断保存...')
            self.save_breakpoint(data)
            print('断点已成功保存！程序结束。')
            return
        
        #断点继续：收尾
        if os.path.exists('spider-noverl-temp.json'):
            os.remove('spider-noverl-temp.json')  
        print(f'\n小说{self.novel_name}已下载完毕，并已保存至{self.novel_name}.txt文档内！')
        print('其中，有{}章下载失败。'.format(len(failure_list)))
        for i in failure_list:
#            print(str(i), end=' ')
            print(str(i))
            
            
def signal_handler(signalum, frame):
    """
    
    """
    print('收到信号：', signalum, frame)
    print("键盘输入终止信号！程序将停止。")
    #单纯只是引发一个异常难以保证程序立即退出，因为程序中存在try嵌套
    #解决思路1：放弃粗枝大叶式异常处理（BaseException or Exception）。即本程序处理思路
    #解决思路2：在每个异常处理except前，优先处理本函数引发的异常，并直接停止程序运行
    raise RuntimeError           
            
if __name__ == "__main__":
    
    
    pass
            

        
        
    
    