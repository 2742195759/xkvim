#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File               :   vim_uilts.py
@Time               :   2021-08-21
@Author             :   Kun Xiong
@Contact            :   xk18@mails.tsinghua.edu.cn
@Last Modified by   :   2022-02-10
@Last Modified time :   2022-02-10

This file contain some vim helper function.

called by the other part of the script.
'''

import vim

def GetCurrentLine():
    """
    get the line of current cursor.
    """
    return vim.eval("getline('.')")


def GetCursorXY():
    """
    get the [int, int] position of cursor.
    """
    return [ int(i) for i in vim.eval("getpos('.')")[1:3]]


def SetCurrentLine(text):
    """
    set current line to text.
    """
    lnum, cnum = GetCursorXY()
    return vim.eval("setline(%d, '%s')"%(int(lnum), text))
