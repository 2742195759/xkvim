export http_proxy=http://172.19.57.45:3128
export https_proxy=http://172.19.57.45:3128
pr_name=`git symbolic-ref --short -q HEAD`
git push origin $pr_name 
