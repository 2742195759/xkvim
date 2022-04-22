syntax keyword Grep Grep
syntax keyword CTag CTag
syntax match NotFound /Not Found./
syntax keyword YCM  YCM
syntax region Filename oneline start="|" end="|"

hi link Grep Constant
hi link CTag Constant
hi link YCM  Constant
hi link NotFound Error
hi link Filename Exception

