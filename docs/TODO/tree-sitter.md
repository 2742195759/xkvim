#  TreeSitter 库实现语义编辑

Tree Sitter 库内置常见语言的 parser，可以对不同的语言进行语义token级别的跳转和编辑。可以非常大的提高programming 的效率 

TODO：下一步计划：

1. 判断是否 tree sitter 的 nvim 版本可以在 vim 上使用，

2. 如果不可以，那么自己利用jobs特性来实现一个功能简小精悍的 tree sitter wrapper。类似 LSP 一样。


## Tree Sitter Usage 调研

[tree sitter 项目官网](https://tree-sitter.github.io/tree-sitter/using-parsers)

里面有一个 play ground 可以感受到 tree sitter 的强大。incremental 的 parser 非常适合在编辑器中集成。

这个Session介绍简单的概念和如何基于Haskell实现vim到tree-sitter的插件。（为什么使用haskell：只是为了逃离舒适区）
