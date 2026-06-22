# ④产业转化 专利处理留痕

- 源:智慧芽导出 12 份(2019-2025),data/external/i_conversion/202606*.XLSX(gitignore)。
- 检索式:IPC:(G06N* OR G06V* OR G06F* OR G06Q* OR G06T* OR G16Y* OR H04L* OR G10L15*
  OR G10L17* OR G06K9* OR B25J* OR G05B* OR G05D* OR H04W*) AND APD:[2019 to 2025]
  AND PATENT_TYPE:("A" OR "U") AND AN_ADD/BI_ADD/IN_ADDRESS:(福建)。
- 处理(scripts/build_i_conversion.py,按i_caliber_patent.yml):去重75396→入账35169;
  剔高校/个人12769、IPC不入C/B/X 14197(检索尾部OR带入的发明人在闽非AI专利,已滤)、
  超窗2025 13214、归市失败47。
- 口径:申请年计;发明+实用新型;第一申请人企业(高校/个人剔,含"有限公司"不误杀);
  IPC前缀C⊂B⊂X(G06K9旧码归C);第一申请人地址归9市,工商注册地兜底。
- ⚠ 第一发明人地址仅24%有值→创新外流率/本地闭环率(描述性,不进CCD)暂不可全算,
  需要时补导发明人地址字段。
