let s:cache = {}

fu! cache#New()
  let res =  deepcopy(s:cache)
  let res.mmap = {}
  return res
endf

fu! s:cache.Get(key)
  if string(get(self.mmap, a:key, 0)) == string(0)
    let result = self.proc()
    let self.mmap[a:key] = result
  endif
  return self.mmap[a:key]
endf

fu! s:cache.Clear()
  let self.mmap = {}
endf

fu! s:cache.SetFunc(func)
  let self.proc = a:func
endf
