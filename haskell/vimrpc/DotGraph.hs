{-# LANGUAGE OverloadedStrings #-}
module DotGraph (generateDotGraph) where
import Debug.Trace (trace)
import qualified Data.Text as T

-- Inputs : graph_strings: "first -> second(weight)\nsecond -> third(weight)"
-- Outputs: Dot
generateDotGraph :: T.Text -> T.Text
generateDotGraph inputs = let graph_lines = filter (/= "") $ T.lines inputs
                          in  wrapDigraph $  dotBody (map parseGraphLine graph_lines)

parseGraphLine :: T.Text -> (T.Text, T.Text, T.Text)
parseGraphLine line = let left = (T.splitOn "(" line) !! 0
                          right = (T.splitOn "(" line) !! 1
                          f = (T.splitOn "->" left) !! 0
                          s = (T.splitOn "->" left) !! 1
                          w = (T.splitOn ")" right) !! 0
                      in  (T.strip f, T.strip s, T.strip w)

dotBody :: [(T.Text, T.Text, T.Text)] -> T.Text
dotBody = Prelude.foldr appendline ""  
    where appendline :: (T.Text, T.Text, T.Text) -> T.Text -> T.Text
          appendline (f, t, w) acc = mconcat [f, "-> ", t, " [ label = ", w, " ] \n", acc] 

wrapDigraph content = mconcat ["digraph g {\nnode [shape=plaintext]\n", content, "}"]

main :: IO()
main = let xxx = "x -> m(12)\ng -> z(11)\n"
       in  putStrLn $ show $ generateDotGraph xxx
