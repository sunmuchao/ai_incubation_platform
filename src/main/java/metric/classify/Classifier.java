package metric.classify;

import base.config.Application;
import base.file.RemoteFileUtils;
import buriedPoint.DBUtils;
import buriedPoint.Temporary;
import metric.MetricPostProcessor;
import metric.MetricNode;
import metric.lineInfo.AggregateLineInfo;
import metric.lineInfo.FilterLineInfo;
import metric.lineInfo.JoinLineInfo;
import metric.lineInfo.LineInfo;
import metric.lineInfo.NormalLineInfo;
import metric.lineInfo.UnionLineInfo;

import java.io.File;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;


public class Classifier {
    public String classify(MetricNode curNode, File metricFile) throws Exception {
        DBUtils dbUtils = Application.getDBUtilsInstance();
        MetricPostProcessor processor = new MetricPostProcessor();
        LineInfo lineInfo = processor.process(curNode);

        //将数据划分区间，创建目录，写入数据库
        String dirName = RecordToDB(dbUtils, lineInfo, curNode.getDate());
        if (dirName == null) return "不需要被记录";
        System.out.println("目录名:" + dirName);
        RemoteFileUtils fileUtils = Application.getRemoteFileUtilsInstance();
        Boolean isExistDir = fileUtils.isExistDirectly(dirName);
        fileUtils.upload(dirName, metricFile);
        if (isExistDir) {
            return null;
        } else {
            return dirName;
        }
    }

    private String getRangeString(String FieldName, int FieldNumber) {
        return FieldName + " BETWEEN " + FieldNumber * 0.9 +
                " and " + FieldNumber * 1.1 + "  and ";
    }

    private boolean isInRange(int lower_limit, int FieldNumber) {
        if (FieldNumber <= lower_limit * 1.1 && FieldNumber >= lower_limit * 0.9) return true;
        return false;
    }

    private String RecordToDB(DBUtils dbUtils, LineInfo lineInfo, String date) throws SQLException {
        String dirName = null;
        int isBug = 0;
        if (lineInfo.getClass().getName().contains("AggregateLineInfo")) {
            AggregateLineInfo aggregateLineInfo = (AggregateLineInfo) lineInfo;

            dirName = aggregateLineInfo.getCurTableInfo().getOperate() + "_" +
                    getRoughInterval(aggregateLineInfo.getCurTableInfo().getRows()) + "_" +
                    getDetailedInterval(aggregateLineInfo.getCurTableInfo().getCols()) + "_" +
                    getDetailedInterval(aggregateLineInfo.getCurTableInfo().getGroupFields().length) + "_" +
                    getDetailedInterval(aggregateLineInfo.getCurTableInfo().getAggFields().length) + "_" +
                    getRoughInterval(aggregateLineInfo.getSonTableInfo().getRows()) + "_" +
                    getDetailedInterval(aggregateLineInfo.getSonTableInfo().getCols()) + "_";

            String rowRange = getRangeString("cur_row_Interval", aggregateLineInfo.getCurTableInfo().getRows());
            String colRange = getRangeString("cur_col_Interval", aggregateLineInfo.getCurTableInfo().getCols());
            String groupRange = getRangeString("cur_group_field_number", aggregateLineInfo.getCurTableInfo().getGroupFields().length);
            String aggRange = getRangeString("cur_group_field_number", aggregateLineInfo.getCurTableInfo().getAggFields().length);
            String lastRowRange = getRangeString("last_row_Interval", aggregateLineInfo.getSonTableInfo().getRows());
            String lastColRange = getRangeString("last_col_interval", aggregateLineInfo.getSonTableInfo().getCols());


            ResultSet rs = dbUtils.SelectData("select min(compute_time + open_time)*1.1 from polars_metric_classifier where operate = \"" +
                    aggregateLineInfo.getCurTableInfo().getOperate() + "\" and " +
                    rowRange +
                    colRange +
                    groupRange +
                    aggRange +
                    lastRowRange +
                    lastColRange +
                    "date <= \"" + Application.publishedLastVersionDate + "\";"
            );

            if (rs.next()) {
                System.out.println("上一个版本的平均值:" +rs.getInt(1));
                System.out.println("当前请求的总耗时:" + (aggregateLineInfo.getCurTableInfo().getComputeTime() + aggregateLineInfo.getCurTableInfo().getOpenTime()));
                if (rs.getInt(1) > 0 && rs.getInt(1) < aggregateLineInfo.getCurTableInfo().getComputeTime()
                        + aggregateLineInfo.getCurTableInfo().getOpenTime()) {
                    //认为当前任务超时,去数据库查看是否存在当前任务，如果不存在就设置isbug为true
                    rs = dbUtils.SelectData("select isBug from polars_metric_classifier where operate = \"" +
                            aggregateLineInfo.getCurTableInfo().getOperate() + "\" and " +
                            rowRange +
                            colRange +
                            groupRange +
                            aggRange +
                            lastRowRange +
                            lastColRange +
                            "date > \"" + Application.publishedLastVersionDate + "\";"
                    );
                    while (rs.next()) {
                        if (rs.getInt(1) == 1) {
                            isBug = 0;
                            break;
                        }
                        isBug = 1;
                    }
                    if(isBug == 1) Temporary.setIsBug(isBug);
                }
            }

            //将数据写入数据库
            dbUtils.updateData("INSERT INTO polars_metric_classifier SET " +
                    "operate=\"" + aggregateLineInfo.getCurTableInfo().getOperate() + "\"," +
                    "cur_row_Interval=" + aggregateLineInfo.getCurTableInfo().getRows() + "," +
                    "cur_col_Interval=" + aggregateLineInfo.getCurTableInfo().getCols() + "," +
                    "cur_group_field_number=" + aggregateLineInfo.getCurTableInfo().getGroupFields().length + "," +
                    "cur_agg_field_number=" + aggregateLineInfo.getCurTableInfo().getAggFields().length + "," +
                    "last_row_Interval=\"" + aggregateLineInfo.getSonTableInfo().getRows() + "\"," +
                    "last_col_interval=\"" + aggregateLineInfo.getSonTableInfo().getCols() + "\"," +
                    "compute_time=" + aggregateLineInfo.getCurTableInfo().getComputeTime() + "," +
                    "open_time=" + aggregateLineInfo.getCurTableInfo().getOpenTime() + "," +
                    "date=\"" + date + "\"," +
                    "isBug=" + isBug + ";"
            );

        } else if (lineInfo.getClass().getName().contains("JoinLineInfo")) {
            JoinLineInfo joinLineInfo = (JoinLineInfo) lineInfo;

            dirName = joinLineInfo.getCurTableInfo().getOperate() + "_" +
                    getRoughInterval(joinLineInfo.getCurTableInfo().getRows()) + "_" +
                    getDetailedInterval(joinLineInfo.getCurTableInfo().getCols()) + "_" +
                    getRoughInterval(joinLineInfo.getLeftTableInfo().getRows()) + "#" +
                    getRoughInterval(joinLineInfo.getRightTableInfo().getRows()) + "_" +
                    getDetailedInterval(joinLineInfo.getLeftTableInfo().getCols()) + "#" +
                    getDetailedInterval(joinLineInfo.getRightTableInfo().getCols());

            String rowRange = getRangeString("cur_row_Interval", getRoughInterval(joinLineInfo.getCurTableInfo().getRows()));
            String colRange = getRangeString("cur_col_Interval", getDetailedInterval(joinLineInfo.getCurTableInfo().getCols()));

            ResultSet rs = dbUtils.SelectData("select last_row_Interval, last_col_interval, min(compute_time + open_time)*1.1 from polars_metric_classifier where operate = \"" +
                    joinLineInfo.getCurTableInfo().getOperate() + "\" and " +
                    rowRange +
                    colRange +
                    "date <= \"" + Application.publishedLastVersionDate + "\";"
            );
            if (rs.next()) {
                String last_row_Interval = rs.getString(1);
                String last_col_interval = rs.getString(2);
                int avg_time = rs.getInt(3);

                if (    last_row_Interval != null &&
                        isInRange(joinLineInfo.getLeftTableInfo().getRows(), Integer.parseInt(last_row_Interval.split(",")[0])) &&
                        isInRange(joinLineInfo.getRightTableInfo().getRows(), Integer.parseInt(last_row_Interval.split(",")[1])) &&
                        isInRange(joinLineInfo.getLeftTableInfo().getCols(), Integer.parseInt(last_col_interval.split(",")[0])) &&
                        isInRange(joinLineInfo.getRightTableInfo().getCols(), Integer.parseInt(last_col_interval.split(",")[1]))) {
                    if (avg_time > 0 && avg_time < (joinLineInfo.getCurTableInfo().getComputeTime() + joinLineInfo.getCurTableInfo().getOpenTime())) {
                        //认为当前任务超时,去数据库查看是否存在当前任务，如果不存在就设置isbug为true
                        rs = dbUtils.SelectData("select last_row_Interval, last_col_interval, isBug from polars_metric_classifier where operate = \"" +
                                joinLineInfo.getCurTableInfo().getOperate() + "\" and " +
                                rowRange +
                                colRange +
                                "date > \"" + Application.publishedLastVersionDate + "\";"
                        );
                        while (rs.next()) {
                            last_row_Interval = rs.getString(1);
                            last_col_interval = rs.getString(2);
                            System.out.println("上一个版本的平均值:" +rs.getInt(1));
                            System.out.println("当前请求的总耗时:" + (joinLineInfo.getCurTableInfo().getComputeTime() + joinLineInfo.getCurTableInfo().getOpenTime()));
                            if (
                                    isInRange(joinLineInfo.getLeftTableInfo().getRows(), Integer.parseInt(last_row_Interval.split(",")[0])) &&
                                    isInRange(joinLineInfo.getRightTableInfo().getRows(), Integer.parseInt(last_row_Interval.split(",")[1])) &&
                                    isInRange(joinLineInfo.getLeftTableInfo().getCols(), Integer.parseInt(last_col_interval.split(",")[0])) &&
                                    isInRange(joinLineInfo.getRightTableInfo().getCols(), Integer.parseInt(last_col_interval.split(",")[1]))) {
                                if (rs.getInt(3) == 1) {
                                    isBug = 0;
                                    break;
                                }
                            }
                            isBug = 1;
                        }
                        if(isBug == 1) Temporary.setIsBug(isBug);
                    }
                }
            }

            //将数据写入数据库
            dbUtils.updateData("INSERT INTO polars_metric_classifier SET " +
                    "operate=\"" + joinLineInfo.getCurTableInfo().getOperate() + "\"," +
                    "cur_row_Interval=" + joinLineInfo.getCurTableInfo().getRows() + "," +
                    "cur_col_Interval=" + joinLineInfo.getCurTableInfo().getCols() + "," +
                    "last_row_Interval=\"" +
                    joinLineInfo.getLeftTableInfo().getRows() + "#" +
                    joinLineInfo.getRightTableInfo().getRows() + "\"," +
                    "last_col_interval=\"" +
                    joinLineInfo.getLeftTableInfo().getCols() + "#" +
                    joinLineInfo.getRightTableInfo().getCols() + "\"," +
                    "compute_time=" + joinLineInfo.getCurTableInfo().getComputeTime() + "," +
                    "open_time=" + joinLineInfo.getCurTableInfo().getOpenTime() + "," +
                    "date=\"" + date + "\"," +
                    "isBug=" + isBug + ";"
            );
        } else if (lineInfo.getClass().getName().contains("UnionLineInfo")) {
            UnionLineInfo unionLineInfo = (UnionLineInfo) lineInfo;
            ArrayList<LineInfo> sonTableInfos = unionLineInfo.getSonTableInfos();
            int last_row_Interval = getRoughInterval(sonTableInfos.get(0).getRows());
            int last_col_interval = getDetailedInterval(sonTableInfos.get(0).getCols());

            dirName = unionLineInfo.getCurTableInfo().getOperate() + "_" +
                    getRoughInterval(unionLineInfo.getCurTableInfo().getRows()) + "_" +
                    getDetailedInterval(unionLineInfo.getCurTableInfo().getCols()) + "_" +
                    getDetailedInterval(sonTableInfos.size()) + "_" +
                    last_row_Interval + "_" +
                    last_col_interval;

            //将数据写入数据库
            dbUtils.updateData("INSERT INTO polars_metric_classifier SET " +
                    "operate=\"" + unionLineInfo.getCurTableInfo().getOperate() + "\"," +
                    "cur_row_Interval=" + unionLineInfo.getCurTableInfo().getRows() + "," +
                    "cur_col_Interval=" + unionLineInfo.getCurTableInfo().getCols() + "," +
                    "last_row_Interval=\"" + last_row_Interval + "\"," +
                    "last_col_interval=\"" + last_col_interval + "\"," +
                    "compute_time=" + unionLineInfo.getCurTableInfo().getComputeTime() + "," +
                    "open_time=" + unionLineInfo.getCurTableInfo().getOpenTime() + "," +
                    "date=\"" + date + "\";"
            );
        } else if (lineInfo.getClass().getName().contains("FilterLineInfo")) {

            FilterLineInfo filterLineInfo = (FilterLineInfo) lineInfo;
            int formulaUUID = filterLineInfo.getCurTableInfo().getFormula().hashCode();
            dirName = filterLineInfo.getCurTableInfo().getOperate() + "_" +
                    getRoughInterval(filterLineInfo.getCurTableInfo().getRows()) + "_" +
                    getDetailedInterval(filterLineInfo.getCurTableInfo().getCols()) + "_" +
                    getRoughInterval(filterLineInfo.getSonTableInfo().getRows()) + "_" +
                    getDetailedInterval(filterLineInfo.getSonTableInfo().getCols()) + "_" +
                    formulaUUID;

            String rowRange = getRangeString("cur_row_Interval", filterLineInfo.getCurTableInfo().getRows());
            String colRange = getRangeString("cur_col_Interval", filterLineInfo.getCurTableInfo().getCols());
            String lastRowRange = getRangeString("last_row_Interval", filterLineInfo.getSonTableInfo().getRows());
            String lastColRange = getRangeString("last_col_interval", filterLineInfo.getSonTableInfo().getCols());


            ResultSet rs = dbUtils.SelectData("select min(compute_time + open_time)*1.1 from polars_metric_classifier where operate = \"" +
                    filterLineInfo.getCurTableInfo().getOperate() + "\" and " +
                    rowRange +
                    colRange +
                    lastRowRange +
                    lastColRange +
                    "date <= \"" + Application.publishedLastVersionDate + "\";"
            );

            if (rs.next()) {
                System.out.println("上一个版本的平均值:" +rs.getInt(1));
                System.out.println("当前请求的总耗时:" + (filterLineInfo.getCurTableInfo().getComputeTime() + filterLineInfo.getCurTableInfo().getOpenTime()));
                if (rs.getInt(1) > 0 && rs.getInt(1) < filterLineInfo.getCurTableInfo().getComputeTime()
                        + filterLineInfo.getCurTableInfo().getOpenTime()) {
                    //认为当前任务超时,去数据库查看是否存在当前任务，如果不存在就设置isbug为true
                    rs = dbUtils.SelectData("select isBug from polars_metric_classifier where operate = \"" +
                            filterLineInfo.getCurTableInfo().getOperate() + "\" and " +
                            rowRange +
                            colRange +
                            lastRowRange +
                            lastColRange +
                            "date > \"" + Application.publishedLastVersionDate + "\";"
                    );
                    while (rs.next()) {
                        if (rs.getInt(1) == 1) {
                            isBug = 0;
                            break;
                        }
                        isBug = 1;
                    }
                    if(isBug == 1) Temporary.setIsBug(isBug);
                }
            }

            //将数据写入数据库
            dbUtils.updateData("INSERT INTO polars_metric_classifier SET " +
                    "operate=\"" + filterLineInfo.getCurTableInfo().getOperate() + "\"," +
                    "cur_row_Interval=" + filterLineInfo.getCurTableInfo().getRows() + "," +
                    "cur_col_Interval=" + filterLineInfo.getCurTableInfo().getCols() + "," +
                    "last_row_Interval=\"" + filterLineInfo.getSonTableInfo().getRows() + "\"," +
                    "last_col_interval=\"" + filterLineInfo.getSonTableInfo().getCols() + "\"," +
                    "formula=\"" + filterLineInfo.getCurTableInfo().getFormula().hashCode() + "\"," +
                    "compute_time=" + filterLineInfo.getCurTableInfo().getComputeTime() + "," +
                    "open_time=" + filterLineInfo.getCurTableInfo().getOpenTime() + "," +
                    "date=\"" + date + "\"," +
                    "isBug=" + isBug + ";"
            );
        } else {
            NormalLineInfo normalLineInfo = (NormalLineInfo) lineInfo;
            dirName = normalLineInfo.getCurTableInfo().getOperate() + "_" +
                    getRoughInterval(normalLineInfo.getCurTableInfo().getRows()) + "_" +
                    getDetailedInterval(normalLineInfo.getCurTableInfo().getCols()) + "_" +
                    getRoughInterval(normalLineInfo.getSonTableInfo().getRows()) + "_" +
                    getDetailedInterval(normalLineInfo.getSonTableInfo().getCols());

            String rowRange = getRangeString("cur_row_Interval", normalLineInfo.getCurTableInfo().getRows());
            String colRange = getRangeString("cur_col_Interval", normalLineInfo.getCurTableInfo().getCols());
            String lastRowRange = getRangeString("last_row_Interval", normalLineInfo.getSonTableInfo().getRows());
            String lastColRange = getRangeString("last_col_interval", normalLineInfo.getSonTableInfo().getCols());


            ResultSet rs = dbUtils.SelectData("select min(compute_time + open_time)*1.1 from polars_metric_classifier where operate = \"" +
                    normalLineInfo.getCurTableInfo().getOperate() + "\" and " +
                    rowRange +
                    colRange +
                    lastRowRange +
                    lastColRange +
                    "date <= \"" + Application.publishedLastVersionDate + "\";"
            );

            if (rs.next()) {
                System.out.println("上一个版本的平均值:" +rs.getInt(1));
                System.out.println("当前请求的总耗时:" + (normalLineInfo.getCurTableInfo().getComputeTime() + normalLineInfo.getCurTableInfo().getOpenTime()));

                if (rs.getInt(1) > 0 && rs.getInt(1) < normalLineInfo.getCurTableInfo().getComputeTime()
                        + normalLineInfo.getCurTableInfo().getOpenTime()) {
                    //认为当前任务超时,去数据库查看是否存在当前任务，如果不存在就设置isbug为true
                    rs = dbUtils.SelectData("select isBug from polars_metric_classifier where operate = \"" +
                            normalLineInfo.getCurTableInfo().getOperate() + "\" and " +
                            rowRange +
                            colRange +
                            lastRowRange +
                            lastColRange +
                            "date > \"" + Application.publishedLastVersionDate + "\";"
                    );
                    while (rs.next()) {
                        if (rs.getInt(1) == 1) {
                            isBug = 0;
                            break;
                        }
                        isBug = 1;
                    }
                    if(isBug == 1) Temporary.setIsBug(isBug);
                }
            }

            //将数据写入数据库
            dbUtils.updateData("INSERT INTO polars_metric_classifier SET " +
                    "operate=\"" + normalLineInfo.getCurTableInfo().getOperate() + "\"," +
                    "cur_row_Interval=" + normalLineInfo.getCurTableInfo().getRows() + "," +
                    "cur_col_Interval=" + normalLineInfo.getCurTableInfo().getCols() + "," +
                    "last_row_Interval=\"" + normalLineInfo.getSonTableInfo().getRows() + "\"," +
                    "last_col_interval=\"" + normalLineInfo.getSonTableInfo().getCols() + "\"," +
                    "compute_time=" + normalLineInfo.getCurTableInfo().getComputeTime() + "," +
                    "open_time=" + normalLineInfo.getCurTableInfo().getOpenTime() + "," +
                    "date=\"" + date + "\"," +
                    "isBug=" + isBug + ";"
            );
            if (normalLineInfo.getCurTableInfo().getOperate().equals("TableRowScanOperator") || normalLineInfo.getCurTableInfo().getOperate().equals("TableScanOperator")) {
                return null;
            }
        }
        return dirName;
    }

    public static int getRoughInterval(int number) {
        //区间分类划分， 千、万、十万、百万、千万、亿
        int interval = 0;
        char[] c = String.valueOf(number).toCharArray();
        if (c.length >= 4) {
            //interval = (int) ((Integer.parseInt(String.valueOf(c[0])) * 10) * Math.pow(10, c.length - 2));
            interval = (int) ((1 * Math.pow(10, c.length - 1)));
        } else {
            if (String.valueOf(c[0]).contains("-")) {
                interval = (Integer.parseInt(String.valueOf(c[1]))) * -1;
            } else {
                interval = 1000;
            }
        }

        return interval;
    }

    public int getDetailedInterval(int number) {
        //区间分类划分， 个、十、百、千、万
        int interval = 0;
        char[] c = String.valueOf(number).toCharArray();
        if (c.length >= 3) {
            interval = (int) ((Integer.parseInt(String.valueOf(c[0])) * 10 + Integer.parseInt(String.valueOf(c[1]))) * Math.pow(10, c.length - 2));
        } else if (c.length == 2) {
            if (String.valueOf(c[0]).contains("-")) {
                interval = (Integer.parseInt(String.valueOf(c[1]))) * -1;
            } else {
                interval = (Integer.parseInt(String.valueOf(c[0]))) * 10;
            }
        } else {
            if (c[0] != '0') {
                interval = 10;
            } else {
                interval = 0;
            }
        }

        return interval;
    }
}
