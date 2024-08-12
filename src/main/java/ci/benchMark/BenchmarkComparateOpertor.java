package ci.benchMark;

import base.db.JSYDBUtils;

/**
 * @author sunmuchao
 * @date 2024/4/26 3:03 下午
 */
public class BenchmarkComparateOpertor {
    //性能上升标准：old != 0 && new != 0 && old > 113% * new  && 87% * old > 100 && |new - old| > 100
    public void performanceRise(String a, String b, String caseName) {
        BenchmarkResultComponent brc = null;
        String uuid_a = JSYDBUtils.query("select uuid from benchmarkResultMetaData where prid=\""+ a +"\" and" +
                " uuid = (select MAX(uuid) FROM benchmarkResultMetaData where prid=\"" + a +"\");");
        String uuid_b = JSYDBUtils.query("select uuid from benchmarkResultMetaData where prid=\""+ b +"\" and" +
                " uuid = (select MAX(uuid) FROM benchmarkResultMetaData where prid=\"" + b +"\");");
        int measureTimetoa  = Integer.parseInt(JSYDBUtils.query("select measureTime FROM benchmarkResult where uuid = \"" + uuid_a + "\"" + " and id=\"" + caseName + "\""));
        int measureTimetob  = Integer.parseInt(JSYDBUtils.query("select measureTime FROM benchmarkResult where uuid = \"" + uuid_b + "\"" + " and id=\"" + caseName + "\""));

        //填充到结果集并且值为true
        BenchmarkResultItem britoa = new BenchmarkResultItem().setMeasureTime(measureTimetoa).setPrid(a);
        BenchmarkResultItem britob = new BenchmarkResultItem().setMeasureTime(measureTimetob).setPrid(b);

        brc = new BenchmarkResultComponent(caseName, britoa, britob);
        if(
               measureTimetoa != 0
               && measureTimetob != 0
               && measureTimetob > 1.13 * measureTimetoa
               && 0.87 * measureTimetob > 100
               && Math.abs(measureTimetoa - measureTimetob) > 100
       ){
           //填充到结果集并且值为true
           brc.isPerformanceRise(true);
       }else{

           //填充到结果集并且值为false
           brc.isPerformanceRise(false);
       }

       BenchmarkResultSet.fillBrc(brc);
    }

    public void performanceReduce(String a, String b, String caseName) {
        //性能下降标准：old != 0 && new != 0 && old < 87% * new && |new - old| > 100
        BenchmarkResultComponent brc = null;
        String uuid_a = JSYDBUtils.query("select uuid from benchmarkResultMetaData where prid=\""+ a +"\" and" +
                " uuid = (select MAX(uuid) FROM benchmarkResultMetaData where prid=\"" + a +"\");");
        String uuid_b = JSYDBUtils.query("select uuid from benchmarkResultMetaData where prid=\""+ b +"\" and" +
                " uuid = (select MAX(uuid) FROM benchmarkResultMetaData where prid=\"" + b +"\");");
        int measureTimetoa  = Integer.parseInt(JSYDBUtils.query("select measureTime FROM benchmarkResult where uuid = \"" + uuid_a + "\"" + "and id=\"" + caseName + "\""));
        int measureTimetob  = Integer.parseInt(JSYDBUtils.query("select measureTime FROM benchmarkResult where uuid = \"" + uuid_b + "\"" + "and id=\"" + caseName + "\""));
        //填充到结果集并且值为true
        BenchmarkResultItem britoa = new BenchmarkResultItem().setMeasureTime(measureTimetoa).setPrid(a);
        BenchmarkResultItem britob = new BenchmarkResultItem().setMeasureTime(measureTimetob).setPrid(b);

        brc = new BenchmarkResultComponent(caseName, britoa, britob);
        if(
                measureTimetoa != 0
                && measureTimetob != 0
                && measureTimetob < 0.87 * measureTimetoa
                && Math.abs(measureTimetoa - measureTimetob) > 100
        ){
            //填充到结果集并且值为true
            brc.isPerformanceReduce(true);
        }else{
            //填充到结果集并且值为false
            brc.isPerformanceReduce(false);
        }
        BenchmarkResultSet.fillBrc(brc);
    }

    public void performancefail(String a, String caseName) {
        //性能失败的标准：new.conFailedCount > 0 || !newCase.getErrorInfo().equals("") || measureTime == 0
        BenchmarkResultComponent brc = null;
        String uuid_a = JSYDBUtils.query("select uuid from benchmarkResultMetaData where prid=\""+ a +"\" and" +
                " uuid = (select MAX(uuid) FROM benchmarkResultMetaData where prid=\"" + a +"\");");
        int measureTimetoa  = Integer.parseInt(JSYDBUtils.query("select measureTime FROM benchmarkResult where uuid = \"" + uuid_a + "\"" + "and id=\"" + caseName + "\""));
        int conFailedCount  = Integer.parseInt(JSYDBUtils.query("select conFailedCount FROM benchmarkResult where uuid = \"" + uuid_a + "\"" + "and id=\"" + caseName + "\""));
        String ErrorInfo  = JSYDBUtils.query("select ErrorInfo FROM benchmarkResult where uuid = \"" + uuid_a + "\"" + "and id=\"" + caseName + "\"");
        BenchmarkResultItem britoa = new BenchmarkResultItem().setPrid(a).setErrorInfo(ErrorInfo).setMeasureTime(measureTimetoa);
        brc = new BenchmarkResultComponent(caseName, britoa, null);
        if(conFailedCount > 0 || measureTimetoa == 0 || !ErrorInfo.equals("")){
            brc.isFail(true);
        }else{
            brc.isFail(false);
        }
        BenchmarkResultSet.fillBrc(brc);
    }

    public void addedCases(String a, String b, String caseName) {
        //a中存在，但是b中不存在
        BenchmarkResultComponent brc = null;
        String uuid_b = JSYDBUtils.query("select uuid from benchmarkResultMetaData where prid=\""+ b +"\" and" +
                " uuid = (select MAX(uuid) FROM benchmarkResultMetaData where prid=\"" + b +"\");");
        String measureTimetob  = JSYDBUtils.query("select measureTime FROM benchmarkResult where uuid = \"" + uuid_b + "\"" + "and id=\"" + caseName + "\"");

        BenchmarkResultItem britoa = new BenchmarkResultItem().setPrid(a);
        BenchmarkResultItem britob = new BenchmarkResultItem().setPrid(b);
        brc = new BenchmarkResultComponent(caseName, britoa, britob);
        //填充到结果集并且值为true
        if(measureTimetob == null){
            //填充到结果集并且值为true
            brc.isNewAdded(true);
        }else{
            //填充到结果集并且值为false
            brc.isNewAdded(false);
        }
        BenchmarkResultSet.fillBrc(brc);
    }
}