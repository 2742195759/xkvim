module Rpc (processHandle) where

import RegisterHandle (autoGenDataType, createProcesser)
import Data.Aeson
import qualified Data.ByteString as BS
import qualified Data.ByteString.Lazy.Char8 as C8
import Data.Maybe
import Data.Text

$(autoGenDataType "Path" [''String])
$(autoGenDataType "IntAdd" [''Int, ''Int])
$(autoGenDataType "Concat" [''String, ''String])
$(autoGenDataType "hi" [])
$(autoGenDataType "echo" [''String])
$(autoGenDataType "add1" [''Int])

add :: (Num a) => a -> a -> a
add x y = x + y

concatFunction :: String -> String -> String
concatFunction x y = x ++ y

hi :: Text
hi = pack "hello, I am a Haskell RPC program based on meta-programming!"

echo :: String -> String
echo x = x

addOne :: Int -> Int
addOne x = x + 1

-- Value -> Either (ErrorInfo String) Value
$(createProcesser "processHandle" [
          ("IntAdd", 'add, 2)
        , ("Concat", 'concatFunction, 2)
        , ("hi", 'hi, 0)
        , ("echo", 'echo, 1)
        , ("add1", 'addOne, 1)
    ])
