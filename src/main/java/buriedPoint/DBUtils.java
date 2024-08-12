package buriedPoint;

import base.config.Application;

import java.sql.*;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

public class DBUtils {
    private static Connection conn;
    public void setConnection(String url) {
        //建立数据库连接
        try {
            Class.forName("com.mysql.jdbc.Driver");
            conn = DriverManager.getConnection(url);
        } catch (ClassNotFoundException | SQLException e) {
            e.printStackTrace();
        }
        this.conn = conn;
    }

    public static void resIntoDB(String traceId, String reason, int isBug, String tableName) {
        if(Application.buriedPointSwitch) {
            Statement statement = null;
            try {
                statement = conn.createStatement();
                SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss");
                ResultSet rs = statement.executeQuery("select * from " + tableName + " where traceId = " + "\"" + traceId + "\"");
                String sql;
                if (rs.next()) {
                    sql = "UPDATE " + tableName + " set reason=" + "\"" + reason + "\"" + ",isBug=" + isBug + " where traceId = " + "\"" + traceId + "\" and trace=null";
                    statement.executeUpdate(sql);
                } else {
                    sql = "INSERT into " + tableName + " values (" + "\"" + traceId + "\"" + ",1," + "\"" + reason + "\"" + "," + isBug + "," + "\"" + sdf.format(new Date()) + "\",null" + ");\n";
                    statement.executeUpdate(sql);
                }
                System.out.println(sql);
            } catch (SQLException throwables) {
                throwables.printStackTrace();
            }
        }
    }

    public static void resIntoDBAndTraceJob(String traceId, ArrayList<String> reasons, int isBug, String tableName, String trace) {
        Statement statement = null;
        try {
            for(String reason : reasons) {
                statement = conn.createStatement();
                SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss");
                ResultSet rs = statement.executeQuery("select * from " + tableName + " where traceId = " + "\"" + traceId + "\" and reason=\"" + reason + "\"");
                String sql;
                if (rs.next()) {
                    sql = "UPDATE " + tableName + " set reason=" + "\"" + reason + "\"" + ",isBug=" + isBug + ",trace=\"" + trace + "\" where traceId = " + "\"" + traceId + "\"";
                    statement.executeUpdate(sql);
                } else {
                    sql = "INSERT into " + tableName + " values (" + "\"" + traceId + "\"" + ",1," + "\"" + reason + "\"" + "," + isBug + "," + "\"" + sdf.format(new Date()) + "\",\"" + trace + "\");\n";
                    statement.executeUpdate(sql);
                }
                System.out.println(sql);
            }
        } catch (SQLException throwables) {
            throwables.printStackTrace();
        }
    }

    public String getPrIdAndBuildId(String dataType){
        Statement statement = null;
        String prId = null;
        String buildId = null;
        try {
            statement = conn.createStatement();
            String sql = "select prId,buildId from benchmarkRes_" + dataType + " order by buildId desc;";
            ResultSet res = statement.executeQuery(sql);
            if(res.next()) {
                prId = res.getString(0);
                buildId = res.getString(1);
            }
        } catch (SQLException throwables) {
            throwables.printStackTrace();
        }

        System.out.println(prId + "_" + buildId);
        return prId + "_" + buildId;
    }

    public void benchmarkIntoDB(String[] line, String mergedPird, int buildId, String branch, String dataType) {
        Statement statement = null;
        try {
            statement = conn.createStatement();
            String sql = "INSERT INTO benchmarkRes_"+dataType+" VALUES(";
            sql += "\"" +mergedPird + "\",\"" + buildId + "\",\"" + branch + "\"," + "\",\"";
            for(String l : line){
                sql += ("\"" + l + "\",");
            }
            sql = sql.substring(0,sql.length() - 1) + ");";
            System.out.println("sql:" + sql);
            statement.execute(sql);
        } catch (SQLException throwables) {
            throwables.printStackTrace();
        }
    }

    public List<String> readBranchName(){
        Statement statement = null;
        List<String> branchNameList = new ArrayList<>();
        try {
            statement = conn.createStatement();
            ResultSet rs = statement.executeQuery("select branchName from ci;");
            while(rs.next()){
                String branchName = rs.getString(1);
                branchNameList.add(branchName);
            }
            rs.close();
        }catch (SQLException throwables) {
            throwables.printStackTrace();
        }
        return branchNameList;
    }

    public void updateData(String sql) throws SQLException {
        Statement statement = null;
        int queryTimes = 0;
        try {
            statement = conn.createStatement();
            statement.executeUpdate(sql);
            System.out.println(sql);
        }catch (SQLException throwables) {
            throwables.printStackTrace();
            statement.setQueryTimeout(5);
        }
        //System.out.println("尝试插入第1次");
        /*while (queryTimes<=5) {
            try {
                if (statement!=null){
                    long start = System.currentTimeMillis();
                    statement.executeUpdate(sql);
                    long end = System.currentTimeMillis();
                    System.out.println("执行时间为" + (end -start));
                    statement.close();
                    return true;
                }
                break;
            }catch (SQLException throwables) {
                if (throwables instanceof MySQLTimeoutException || throwables instanceof CommunicationsException){
                    System.out.println("第"+(queryTimes+1)+"次超时");
                    queryTimes++;
                    System.out.println("尝试插入第"+(queryTimes+1)+"次");
                }else {
                    throwables.printStackTrace();
                    return false;
                }
            }
        }*/
        /*if (queryTimes>=6){
            System.out.println("5次尝试全部超时，程序不再执行");
            return false;
        }else {
            return true;
        }*/
    }

    public ResultSet SelectData(String sql){
        Statement statement = null;
        ResultSet rs = null;
        try {
            System.out.println(sql);
            statement = conn.createStatement();
            rs = statement.executeQuery(sql);
        }catch (SQLException throwables) {
            throwables.printStackTrace();
        }
        return rs;
    }

    public boolean isExistData(String sql) throws SQLException {
        Statement statement = null;
        ResultSet rs = null;
        try {
            statement = conn.createStatement();
            rs = statement.executeQuery(sql);
            if(rs.getString(0).equals("")) return false;
        }catch (SQLException throwables) {
            throwables.printStackTrace();
        }
        System.out.println("true");
        return true;
    }

}