#!/bin/bash

# FreeStyle每周四安全更新脚本
# 使用方法: ./update_weekly_safe.sh

echo "🚀 开始FreeStyle每周安全更新流程..."
echo "=================================="

# 检查更新包目录
if [ ! -d "../fsupdate" ]; then
    echo "❌ 错误: 未找到更新包目录 ../fsupdate/"
    echo "请先将更新包解压到 FS解析/fsupdate/ 目录"
    exit 1
fi

echo "✅ 找到更新包目录"

# 创建备份目录
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
echo "📁 创建备份目录: $BACKUP_DIR"

# 备份重要文件
echo "💾 备份重要文件..."
cp index.html "$BACKUP_DIR/"
cp qr_code.html "$BACKUP_DIR/"
cp image_data.js "$BACKUP_DIR/" 2>/dev/null || echo "⚠️ 没有找到旧的image_data.js"
cp *.md "$BACKUP_DIR/" 2>/dev/null || echo "⚠️ 没有找到Markdown文件"
cp *.sh "$BACKUP_DIR/" 2>/dev/null || echo "⚠️ 没有找到脚本文件"

# 清理所有图片相关文件夹
echo "🧹 清理所有旧的图片文件夹..."
find . -maxdepth 1 -type d \( -name "res*" -o -name "ur_*" -o -name "u_*" -o -name "icon*" -o -name "effect*" -o -name "title*" -o -name "ActionSlot*" -o -name "sap*" \) -exec rm -rf {} + 2>/dev/null || true

# 清理旧的图片数据文件
echo "🗑️ 清理旧的图片数据文件..."
rm -f image_data.js
rm -f image_data_backup_*.js

echo "✅ 清理完成"

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

# 复制新的图片文件夹
echo "🖼️ 复制新的图片文件夹..."
cp -r fsupdate_extracted_images/* fsupdate_github_pages/
echo "✅ 已复制新的图片文件夹"

# 返回GitHub Pages目录
cd fsupdate_github_pages

# 检查文件数量
echo "📊 检查更新结果..."
NEW_IMAGE_COUNT=$(find . -name "*.png" -o -name "*.jpg" | wc -l)
echo "✅ 新图片数量: $NEW_IMAGE_COUNT"

# 检查Git状态
echo "🔍 检查Git状态..."
git status

# 添加所有文件
echo "📝 添加文件到Git..."
git add .

# 提交更改
COMMIT_MSG="完全更新FreeStyle图片资源 - $(date +%Y-%m-%d) - 图片数量: $NEW_IMAGE_COUNT"
echo "💾 提交更改: $COMMIT_MSG"
git commit -m "$COMMIT_MSG"

# 推送到GitHub
echo "🚀 推送到GitHub..."
git push origin main

if [ $? -eq 0 ]; then
    echo "✅ 安全更新成功完成！"
    echo "🌐 网站地址: https://laofeifs.github.io/fsupdate-gallery/"
    echo "📱 二维码页面: https://laofeifs.github.io/fsupdate-gallery/qr_code.html"
    echo "📁 备份位置: $BACKUP_DIR"
else
    echo "❌ 推送失败，请检查网络连接或重试"
    echo "📁 备份文件在: $BACKUP_DIR"
    exit 1
fi

echo "=================================="
echo "🎉 FreeStyle每周安全更新流程完成！"
echo "💡 提示: 旧文件已备份到 $BACKUP_DIR 目录" 