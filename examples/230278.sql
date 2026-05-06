SELECT
    cast(
        to_char(to_date(ht.period_name, 'MON-YY'), 'YYYYMM') AS int
    ) AS period_id,
    gl.ledger_category_code,
    lt.coa_company_code,
    st.sr1,
    sum(coalesce(lt.entered_dr, 0)) AS entered_dr
FROM
    sdifin.ogg_hah_ae_header_8663_vi ht,
    sdifin.ogg_hah_ae_line_8663_vi lt,
    (
        SELECT
            st.ae_header_id,
            st.ae_line_num,
            st.sr1
        FROM
            sdifin.ogg_hah_ae_line_sr_8663_vi st
    ) st,
    sdifin.ogg_gsc_ledgers_t_8663 gl
WHERE
    ht.ae_header_id = lt.ae_header_id
    AND lt.ae_header_id = st.ae_header_id
    AND lt.ae_line_num = st.ae_line_num
    AND ht.je_transfer_status_code <> 'NT'
    AND ht.ledger_short_name = gl.ledger_short_name
GROUP BY
    cast(
        to_char(to_date(ht.period_name, 'MON-YY'), 'YYYYMM') AS int
    ),
    gl.ledger_category_code,
    lt.coa_company_code,
    st.sr1