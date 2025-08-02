#!/bin/bash

# 街头篮球图片集 GitHub Pages 部署脚本
# 老非制作

echo "🚀 开始部署街头篮球图片集到GitHub Pages..."

# 检查是否在正确的目录
if [ ! -f "index.html" ]; then
    echo "❌ 错误：请在包含index.html的目录中运行此脚本"
    exit 1
fi

# 检查Git状态
if [ ! -d ".git" ]; then
    echo "❌ 错误：当前目录不是Git仓库"
    exit 1
fi

# 提示用户输入GitHub用户名
echo "📝 请输入您的GitHub用户名："
read github_username

if [ -z "$github_username" ]; then
    echo "❌ 错误：GitHub用户名不能为空"
    exit 1
fi

# 提示用户输入仓库名
echo "📝 请输入GitHub仓库名（建议：fsupdate-gallery）："
read repo_name

if [ -z "$repo_name" ]; then
    repo_name="fsupdate-gallery"
fi

# 添加远程仓库
echo "🔗 添加远程仓库..."
git remote remove origin 2>/dev/null
git remote add origin "https://github.com/$github_username/$repo_name.git"

# 推送代码
echo "📤 推送代码到GitHub..."
git branch -M main
git push -u origin main

if [ $? -eq 0 ]; then
    echo "✅ 代码推送成功！"
    echo ""
    echo "🌐 接下来请手动完成以下步骤："
    echo "1. 访问 https://github.com/$github_username/$repo_name"
    echo "2. 点击 'Settings' 标签"
    echo "3. 在左侧菜单找到 'Pages'"
    echo "4. Source 选择 'Deploy from a branch'"
    echo "5. Branch 选择 'main'，Folder 选择 '/ (root)'"
    echo "6. 点击 'Save'"
    echo ""
    echo "📱 部署完成后，您的网站地址将是："
    echo "https://$github_username.github.io/$repo_name/"
    echo ""
    echo "🎉 然后就可以将这个链接分享给微信好友了！"
else
    echo "❌ 推送失败，请检查："
    echo "1. GitHub用户名是否正确"
    echo "2. 仓库是否已创建"
    echo "3. 网络连接是否正常"
fi 