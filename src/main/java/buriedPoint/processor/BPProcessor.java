package buriedPoint.processor;

import buriedPoint.DBUtils;
import buriedPoint.point.BuriedPoint;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class BPProcessor {
    private DBUtils dbUtils;
    private String traceid;
    private BuriedPoint buriedPoint;
    private String cookie;

    public BPProcessor(BuriedPoint buriedPoint, DBUtils dbUtils, String traceid, String cookie) {
        this.buriedPoint = buriedPoint;
        this.dbUtils = dbUtils;
        this.traceid = traceid;
        this.cookie = cookie;
    }

    public void process() throws Exception {
    }


    //判断当前耗时是否跟之前的耗时有变化，如果有小变化就保持旧耗时。 如果变化大的话就记录新耗时
    //如果判断是否有大的耗时变化:耗时膨胀为原来的2倍的耗时
    public boolean judgeDuplicateBug() throws SQLException {
        Boolean duplicateBug = false;
        ResultSet rs = null;
        String curTableName = null;
        float minTotalTime = Long.MAX_VALUE;
        if (!(buriedPoint.getTableName() == null && buriedPoint.getWidgetName() == null)) {
            rs = dbUtils.SelectData("select * from BuriedPointUserMessage;");

            if (buriedPoint.getTableName() != null) {
                curTableName = buriedPoint.getTableName();
            } else if (buriedPoint.getWidgetName() != null) {
                curTableName = buriedPoint.getWidgetName();
            }

            while (rs.next()) {
                String username = rs.getString(1);
                String tablename = rs.getString(2);
                float totalTime = rs.getFloat(3);
                float upDateTotalTime = rs.getFloat(4);

                if (isSimilarTable(buriedPoint.getUserName(), username, curTableName, tablename)) {
                    if (buriedPoint.getClass().getName().contains("UpdateBuriedPoint")) {
                        if(totalTime != 0){
                            duplicateBug = true;
                            dbUtils.updateData("UPDATE BuriedPointUserMessage set updateTime=" + buriedPoint.getTotalTime() + " where table_name=\"" + tablename + "\" and user_name=\"" + username + "\";");
                            dbUtils.resIntoDB(traceid, "重复bug:表名=" + curTableName, 0, "jsyUpdate");
                        } else if (buriedPoint.getTotalTime() < upDateTotalTime * 2) {
                            duplicateBug = true;
                            minTotalTime = Math.min(upDateTotalTime, buriedPoint.getTotalTime());
                            dbUtils.updateData("UPDATE BuriedPointUserMessage set updateTime=" + minTotalTime + " where table_name=\"" + tablename + "\" and user_name=\"" + username + "\";");
                            dbUtils.resIntoDB(traceid, "重复bug:表名=" + curTableName, 0, "jsyUpdate");
                        } else {
                            dbUtils.updateData("UPDATE BuriedPointUserMessage set updateTime=" + buriedPoint.getTotalTime() + " where table_name=\"" + tablename + "\" and user_name=\"" + username + "\";");
                        }
                    } else {
                        if(upDateTotalTime != 0){
                            duplicateBug = true;
                            dbUtils.updateData("UPDATE BuriedPointUserMessage set time=" + buriedPoint.getTotalTime() + " where table_name=\"" + tablename + "\" and user_name=\"" + username + "\";");
                            dbUtils.resIntoDB(traceid, "重复bug:表名=" + curTableName, 0, "jsy");
                        } else if (buriedPoint.getTotalTime() < totalTime * 2) {
                            //如果当前耗时小于2*数据库记录的耗时的话，并不会更新数据库中的耗时
                            duplicateBug = true;
                            //minTotalTime = Math.min(totalTime, buriedPoint.getTotalTime());
                            //dbUtils.updateData("UPDATE BuriedPointUserMessage set time=" + minTotalTime + " where table_name=\"" + tablename + "\" and user_name=\"" + username + "\";");
                            dbUtils.resIntoDB(traceid, "重复bug:表名=" + curTableName, 0, "jsy");
                        } else {
                            dbUtils.updateData("UPDATE BuriedPointUserMessage set time=" + buriedPoint.getTotalTime() + " where table_name=\"" + tablename + "\" and user_name=\"" + username + "\";");
                        }
                    }
                }
            }
        }
        return duplicateBug;
    }

    //判断是否是相似的表:筛选字符串中所有的英文和汉字，比较字符串是否相等
    //如果表名或者组件名是: 分析表的话，判断用户名是否相同 ，否则的话按照上面的逻辑判断是否是相似表
    private static boolean isSimilarTable(String userName, String usedUserName, String tableName, String usedTableName) {
        StringBuffer sb = new StringBuffer();
        StringBuffer sb1 = new StringBuffer();
        for (int i = 0; i < tableName.length(); i++) {
            char c = tableName.charAt(i);
            if (isEnglish(c) || isChinese(c)) sb.append(c);
        }
        for (int i = 0; i < usedTableName.length(); i++) {
            char c = usedTableName.charAt(i);
            if (isEnglish(c) || isChinese(c)) sb1.append(c);
        }

        if (sb.toString().equals("分析表") || sb.toString().equals("test")) {
            if(userName != null)
                if ((sb.toString()).equals(sb1.toString()) && userName.equals(usedUserName)) return true;
        } else if (!sb.toString().equals("分析表") && !sb.toString().equals("test") && sb.toString().equals(sb1.toString())) {
            return true;
        }
        return false;
    }

    public static boolean isEnglish(char c) {
        if ((c > 'A' && c < 'Z') || (c > 'a' && c < 'z')) {
            return true;
        }
        return false;
    }

    public static boolean isChinese(char c) {
        Pattern pattern = Pattern.compile("[\\u4e00-\\u9fa5]{0,}$");
        Matcher matcher = pattern.matcher(String.valueOf(c));
        if (matcher.matches()) {
            return true;
        }
        return false;
    }
}
