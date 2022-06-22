#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File               :   func_register.py
@Time               :   2021-08-21
@Author             :   Kun Xiong
@Contact            :   xk18@mails.tsinghua.edu.cn
@Last Modified by   :   2022-02-10
@Last Modified time :   2022-02-10

If we want to call a python function, we need to define a vim function
and then implement it by calling the underground python function. 
So we hope to do it in this file and call a register python function when 
we enter vim only once.

1. define a data structure to save the function to be registered.
2. register functions by python vim module, create the correspond vim function.

One Good idea is : 

```
@vim_register(name=None, keymap=None)
def convert(list_of_args):
    pass
```

we can use name and keymap to override the default vim function.
the default name is "Convert", keymap="None"
'''

import vim
import sys
import os

def vim_register(name="", keymap="", command="", with_args=False):
    """
    keymap: i:MAP | MAP
    """
    def decorator(func):
        # register in vim
        nonlocal keymap
        keymap_mode = "noremap"
        if keymap.startswith("i:"):
            keymap_mode = "inoremap"
            keymap = keymap[2:]

        vim_name = name
        if not vim_name : 
            vim_name = func.__name__.capitalize()
            vim_name = "Py%s" % vim_name

        vim.command(
"""
function! %s(list_of_args)
    execute 'py3' 'Xiongkun.%s(vim.eval("a:list_of_args"))'
    return ""
endfunction
"""%(vim_name, func.__name__))

        if keymap != "": 
            vim.command( f"""
{keymap_mode} {keymap} :call {vim_name} ([])<cr>
""")

        if command != "": 
            # split by space,  and pass as string
            arg_num = '0'
            if with_args: arg_num = '*'
            vim.command( """ command! -n=%s %s cal %s(split("<args>", " ")) """%(arg_num, command, vim_name))
        return func
    return decorator


"""
for test, create a PyEcho function in vim environment. echo the first args.
"""
@vim_register()
def echo(args):
    vim.command("echo '%s'" % args[0])

