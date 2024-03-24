import System.Process
import System.IO

main :: IO ()
main = do
     (_, Just hout, _, _) <- createProcess ((proc "ls" []) { std_out = CreatePipe })
     hGetContents hout >>= putStrLn
     return ()
