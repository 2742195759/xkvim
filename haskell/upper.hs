main :: IO (Int)
main = do
     content <- getContents
     print (lines content)
     return 1


