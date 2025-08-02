#!/bin/bash

# FreeStyle每周四更新脚本
# 使用方法: ./update_weekly.sh

echo "🚀 开始FreeStyle每周更新流程..."
echo "=================================="

# 检查更新包目录
if [ ! -d "../fsupdate" ]; then
    echo "❌ 错误: 未找到更新包目录 ../fsupdate/"
    echo "请先将更新包解压到 FS解析/fsupdate/ 目录"
    exit 1
fi

echo "✅ 找到更新包目录"

# 备份当前image_data.js
if [ -f "image_data.js" ]; then
    cp image_data.js image_data_backup_$(date +%Y%m%d_%H%M%S).js
    echo "✅ 已备份当前image_data.js"
fi

# 运行Python分析脚本
echo "📊 运行图片分析脚本..."
cd ..
if [ -f "create_enhanced_image_gallery.py" ]; then
    python create_enhanced_image_gallery.py
    echo "✅ 图片分析完成"
else
    echo "❌ 错误: 未找到分析脚本 create_enhanced_image_gallery.py"
    exit 1
fi

# 复制新的图片数据
echo "📁 复制新的图片数据..."
if [ -f "fsupdate_extracted_images/image_data.js" ]; then
    cp fsupdate_extracted_images/image_data.js fsupdate_github_pages/
    echo "✅ 已复制新的image_data.js"
else
    echo "❌ 错误: 未找到新的image_data.js"
    exit 1
fi

# 复制图片文件夹
echo "🖼️ 复制图片文件夹..."
cp -r fsupdate_extracted_images/* fsupdate_github_pages/
echo "✅ 已复制图片文件夹"

# 返回GitHub Pages目录
cd fsupdate_github_pages

# 检查Git状态
echo "🔍 检查Git状态..."
git status

# 添加所有文件
echo "📝 添加文件到Git..."
git add .

# 提交更改
COMMIT_MSG="更新FreeStyle图片资源 - $(date +%Y-%m-%d)"
echo "💾 提交更改: $COMMIT_MSG"
git commit -m "$COMMIT_MSG"

# 推送到GitHub
echo "🚀 推送到GitHub..."
git push origin main

if [ $? -eq 0 ]; then
    echo "✅ 更新成功完成！"
    echo "🌐 网站地址: https://laofeifs.github.io/fsupdate-gallery/"
    echo "📱 二维码页面: https://laofeifs.github.io/fsupdate-gallery/qr_code.html"
else
    echo "❌ 推送失败，请检查网络连接或重试"
    exit 1
fi

echo "=================================="
echo "🎉 FreeStyle每周更新流程完成！" 