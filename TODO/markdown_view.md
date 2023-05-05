# Markdown 预览器

## 编写一个 markdown 的预览程序

1. 【基础功能：预览】可以使用 vim 来进行编写，同时可以同步使用 OS 自带的预览界面进行预览。
2. 【进阶功能】支持 web 端和 vim 端的行同步。
3. 【进阶功能】支持 web 进行预览，同时支持 web 端的点击事件反馈。包含点击定位等。

## 简单实现：功能 1

直接在 windows 上打开：marktext

[ 问题1 ]: 不支持自动定位。

1. marktext 不支持自动更新.
2. typora 支持自动更新. 0.11.18(5941) 版本支持自动更新.

## 进阶功能：难点

1. 如果是在本地机器开启一个 web 端口，并且在前端处理这类同步，最后通过 vim 的RPC反馈到 vim 上，是一个不错的设计，但是 web 的访问依赖代理。
2. 但是 vim 和 web 创建器在同一个机器，确实方便很多，而且可以由 vim 创建整个 web 控制器。

## 流程

那就是当手机定位很准确的时候.

## 基础版本：命令
1. `MarkdownPreviewUpdate`: 在远程机器上更新当前的 markdown preview 画面。自动命令，每次 save 一个 markdown 时就开始执行。
2. `MarkdownPreviewStart` : 在远程机器上打开预览窗口。并且安装自动 Preview 画面.


## Windows Typora
1. 下载地址

1. 破解方法
https://blog.csdn.net/weixin_46873254/article/details/126326751?spm=1001.2101.3001.6650.1&utm_medium=distribute.pc_relevant.none-task-blog-2%7Edefault%7ECTRLIST%7ERate-1-126326751-blog-125468083.235%5Ev32%5Epc_relevant_default_base3&depth_1-utm_source=distribute.pc_relevant.none-task-blog-2%7Edefault%7ECTRLIST%7ERate-1-126326751-blog-125468083.235%5Ev32%5Epc_relevant_default_base3&utm_relevant_index=2
