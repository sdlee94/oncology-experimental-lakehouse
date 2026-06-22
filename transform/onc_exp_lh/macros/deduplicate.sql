{% macro deduplicate(model, partition_by, order_by) %}
    select * from (
        select
            *,
            row_number() over (
                partition by {{ partition_by }}
                order by {{ order_by }}
            ) as row_num
        from {{ model }}
    )
    where row_num = 1
{% endmacro %}