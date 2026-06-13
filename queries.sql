-- 2023-2025 全量可报专业明细
SELECT
  year,
  school_name,
  official_group_name,
  score,
  major_name,
  tuition,
  study_length,
  elective_info,
  zslx_name
FROM eligible_majors
ORDER BY year, score, school_name, official_group_name, major_name;

-- 按年份查看
SELECT
  year,
  school_name,
  official_group_name,
  score,
  major_name
FROM eligible_majors
WHERE year = 2025
ORDER BY score, school_name, official_group_name, major_name;

-- 查询某个学校的所有可报专业
SELECT
  year,
  school_name,
  official_group_name,
  score,
  major_name,
  tuition,
  study_length,
  elective_info
FROM eligible_majors
WHERE school_name = '湖南第一师范学院'
ORDER BY year, score, official_group_name, major_name;

-- 查询某个专业关键词
SELECT
  year,
  school_name,
  official_group_name,
  score,
  major_name,
  tuition,
  study_length
FROM eligible_majors
WHERE major_name LIKE '%计算机%'
ORDER BY year, score, school_name;

-- 查看未能补齐专业明细的专业组
SELECT
  year,
  school_name,
  official_group_name,
  reason,
  detail
FROM unmatched_groups
ORDER BY year, school_name, official_group_name;

-- 统计库覆盖情况
SELECT
  (SELECT COUNT(*) FROM admission_groups) AS score_group_count,
  (SELECT COUNT(DISTINCT school_name_official) FROM school_mappings WHERE gaokao_school_id IS NOT NULL) AS matched_school_count,
  (SELECT COUNT(*) FROM eligible_majors) AS eligible_major_count,
  (SELECT COUNT(DISTINCT school_name) FROM eligible_majors) AS eligible_school_count,
  (SELECT COUNT(DISTINCT year || '-' || school_name || '-' || official_group_code) FROM eligible_majors) AS eligible_group_count;

-- 查看学校映射来源，便于人工复核
SELECT
  school_name_official,
  gaokao_school_id,
  gaokao_school_name,
  match_type,
  confidence,
  notes
FROM school_mappings
ORDER BY school_name_official;

-- 查看未匹配原因汇总
SELECT
  reason,
  COUNT(*) AS row_count
FROM unmatched_groups
GROUP BY reason
ORDER BY row_count DESC, reason;
