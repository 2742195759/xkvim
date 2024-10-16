# MarkText Previewer

这个功能是专门为 vim 打造的一个 markdown previewer，虽然只是一个previewer，确实
集结了一个专门的『所见即所得』的markdown editor的所有功能。（因为本来就是基于MarkText
魔改的 markdown previewer。）

这里将详细讲解如何使用，方式以后遗忘。

## 在remote machine 下载 marktext-for-vim 

marktext-for-vim 是一个 基于marktext魔改的一个previewer，（@xiongkun）亲自魔改，
花费了四天的晚上时光。

仓库地址：[marktext for vim github 仓库](https://github.com/2742195759/marktext-for-vim)

这里简单介绍一下改动吧，防止遗忘：

1. 在 electron-vue 的架构下添加了一个远程的 controller 线程，这个线程是一个单独的 http 服务，负责监听pc的 3000 端口并处理set-cursor响应。

2. 将marktext的auto save删除，同时当本地文件被修改时，直接丢失所有本地改动，进行reload。（因为作为preview是不需要交互的修改功能的）【后续是否考虑支持图片插入？】

3. 原来的marktext muya markdown 解释器会进行语法修正(比如空行删除等)，会导致源文件的行数不对应。所以这里禁用了这个修改。`dispatch("change")` 的部分被删除了，详情可以见仓库的魔改commit。


有了上述三个修改，同时加上一个 marktext_set_cursor.js 文件，我们可以很好的进行vim的preview：

1. 修改只需要覆盖原来文件，即可以reload，这个直接自然实现。

2. cursor move 只要在 pc 上执行 `node marktext_set_cursor.js {line} {col}` 即可控制 marktext 的cursor移动，可以保持了 vim 同步。


