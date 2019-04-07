#!/bin/bash

# awk '條件類型1{動作1} 條件類型2{動作2} ...' filename
# awk 主要是處理『每一行的欄位內的資料』，而預設的『欄位的分隔符號為 "空白鍵" 或 "[tab]鍵" 』
# 參數 -F fs or --field-separator fs 輸入字串的分隔符
# awk -F ',' {print $3} --> 指定分隔符為","，印出第三個欄位的值

oldUrl=$(cat line_secret_key | awk -F':' '$1 ~ /"server_url"/' | awk -F'"' '{print $4}')
newUrl=$(curl -s "localhost:54088/api/tunnels" | awk -F',' '{print $3}' | awk -F'"' '{print $4}' | awk -F'//' '{print $2}')

# 一定要用雙引號才能保持$變數特性，才不會被當成一般字元
# sed -i i參數代表寫回原本檔案
# mac 的 sed -i 後面必須先加上 "" 才能正常運作
sed -i "" "s|$oldUrl|$newUrl|" line_secret_key

echo ""
echo "======Ngrok======"
echo ""
echo "old_url is $oldUrl"
echo ""
echo "new_url is $newUrl"
echo ""
echo "replacement completed"
echo ""
echo "================="
echo ""





