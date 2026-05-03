SELECT
    t.company_code,
    a.hw_contract_num,
    pa.proj_num,
    pr.prod_code,
    pr2.prod_code AS major_prod_code,
    reg.geo_pc_code,
    cust.cust_en_name,
    cust2.top_cust_category_en_name,
    f.src_sys_code,
    sum(t.tc_amount) AS tc_amount
FROM
    fin_dwl_ja.dwr_fin_rev_cost_cum_f_i t
    LEFT JOIN dwrdim.dwr_dim_contract_d a ON t.contract_key = a.contract_key
    LEFT JOIN dwrdim.dwr_dim_project_d pa ON t.proj_key = pa.proj_key
    LEFT JOIN dwrdim.dwr_dim_product_d pr ON (
        t.prod_key = pr.prod_key
        AND pr.scd_active_ind = 1
    )
    LEFT JOIN dwrdim.dwr_dim_product_d pr2 ON t.major_prod_key = pr2.prod_key
    LEFT JOIN dwrdim.dwr_dim_region_rc_d reg ON t.geo_pc_key = reg.geo_pc_key
    LEFT JOIN dwrdim.dwr_dim_customer_d cust ON t.sign_cust_key = cust.cust_account_key
    LEFT JOIN dwrdim.dwr_dim_customer_d cust2 ON (
        t.end_cust_id = cust2.cust_account_id
        AND cust2.scd_active_ind = 1
    )
    LEFT JOIN dwrdim.dwr_dim_journal_category_d f ON t.je_category_id = f.je_category_id
WHERE
    1 = 1
    AND t.period_id >= 201300
    AND & PERIOD_ID
    AND & HW_CONTRACT_NUM
    AND & PROJ_NUM
GROUP BY
    t.company_code,
    a.hw_contract_num,
    pa.proj_num,
    pr.prod_code,
    pr2.prod_code,
    reg.geo_pc_code,
    cust.cust_en_name,
    cust2.top_cust_category_en_name,
    f.src_sys_code