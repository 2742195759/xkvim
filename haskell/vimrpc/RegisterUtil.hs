module RegisterUtil where
import qualified Data.Char as Char
import Language.Haskell.TH

capitalized :: String -> String
capitalized (head:tail) = Char.toUpper head : tail
capitalized [] = []

uncapitalized :: String -> String
uncapitalized (head:tail) = Char.toLower head : tail
uncapitalized [] = []

getParamName :: String -> Name
getParamName method = mkName $ (capitalized $ method ++ "Param")

getArgNumFuncName :: String -> Name
getArgNumFuncName method = mkName $ (uncapitalized $ method ++ "ArgNumber")

getArgNumFromMethod :: (Quote m) => String -> m Exp
getArgNumFromMethod method = let name = getArgNumFuncName method
                             in varE name

