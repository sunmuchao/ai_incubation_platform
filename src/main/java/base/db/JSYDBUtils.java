package base.db;

import ci.benchMark.PR;
import ci.benchMark.TestResult;
import com.alibaba.druid.pool.DruidDataSource;

import javax.sql.DataSource;
import java.sql.*;
import java.util.*;
import java.util.Map.Entry;

public class JSYDBUtils {
    private static DruidDataSource dataSource;
    private static Connection conn;

    static {
        try {
            dataSource = new DruidDataSource();
            dataSource.setDriverClassName("com.mysql.jdbc.Driver");
            dataSource.setUrl("jdbc:mysql://47.102.211.0:3306/jsy?useUnicode=true&characterEncoding=utf8&autoReconnect=true&useSSL=false&connectTimeOut=60000&socketTimeOut=60000&rewriteBatchedStatements=true");
            dataSource.setUsername("fanruan");
            dataSource.setPassword("Fanruan");
            dataSource.setMaxActive(50);
            dataSource.setMinIdle(5);
            dataSource.setMaxWait(10000);
            dataSource.setConnectionErrorRetryAttempts(3);
            dataSource.init();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static DataSource getDataSource() {
        return dataSource;
    }

    public static Connection getConnection() {
        try { //从连接池中获取连接对象
            if (conn == null || conn.isClosed()) {
                conn = dataSource.getConnection();
            }
        } catch (SQLException e) {
            e.printStackTrace();
        }
        return conn;
    }


    public static Connection beginTx() {
        conn = getConnection();
        try {
            conn.setAutoCommit(false);
        } catch (SQLException throwables) {
            throwables.printStackTrace();
        }
        return conn;
    }

    public static void commit() {
        Connection conn = getConnection();
        try {
            conn.commit();
        } catch (SQLException throwables) {
            throwables.printStackTrace();
        }
    }

    public static void rollback() {
        Connection conn = getConnection();
        try {
            conn.rollback();
        } catch (SQLException throwables) {
            throwables.printStackTrace();
        }
    }


    /**
     * 查询*
     *
     * @param sql        sql语句
     * @param parameters 想要查到的数据列
     * @return 每一行的数据列通过键值对的方式储存到map中，通过list存放多行
     */
    public static List<Map<String, String>> query(String sql, String... parameters) {
        Connection con = null;
        PreparedStatement pst = null;
        ResultSet rs = null;
        List<Map<String, String>> result = new ArrayList<>();
        try {
            System.out.println(sql);
            con = getConnection();
            pst = con.prepareStatement(sql);
            pst.setQueryTimeout(60);
            rs = pst.executeQuery();

            while (rs.next()) {
                Map<String, String> map = new HashMap<>();
                if (parameters.length > 0) {
                    for (String parameter : parameters) {
                        String value = rs.getString(parameter);
                        map.put(parameter, value);
                    }
                }
                result.add(map);
            }
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            close(con, pst, rs);
        }

        return result;
    }

    public static String query(String sql) {
        //Connection con = null;
        PreparedStatement pst = null;
        ResultSet rs = null;
        String res = null;
        System.out.println(sql);
        try {
            conn = getConnection();
            pst = conn.prepareStatement(sql);
            pst.setQueryTimeout(60);
            rs = pst.executeQuery();
            while (rs.next()) {
                res = rs.getString(1);
            }
        } catch (SQLException throwables) {
            throwables.printStackTrace();
        }
        return res;
    }

    public static List<TestResult> queryTestResult(String sql) {
        Connection con = null;
        PreparedStatement pst = null;
        ResultSet rs = null;
        List<TestResult> result = new ArrayList<>();
        try {
            con = getConnection();
            pst = con.prepareStatement(sql);
            pst.setQueryTimeout(60);
            rs = pst.executeQuery();
            System.out.println(sql);
            while (rs.next()) {
                TestResult testResult = new TestResult(rs.getString("class_name_prefix"), Float.valueOf(rs.getString("time")));
                result.add(testResult);
            }
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            close(con, pst, rs);
        }

        return result;
    }


    public static int updateData(String sql) {
        int count = 0;
        //Connection con = null;
        PreparedStatement pst = null;
        try {
            System.out.println(sql);
            conn = getConnection();
            pst = conn.prepareStatement(sql);
            pst.setQueryTimeout(60);
            count = pst.executeUpdate();
        } catch (Exception e) {
            e.printStackTrace();
        }

        return count;
    }

    public static void batchInsert(Map<String, Float> testResults, String uuid) {
        try {
            Connection con = null;
            String insertQuery = "INSERT INTO test_results (uuid, class_name_prefix, time) VALUES (?, ?, ?)";
            con = getConnection();
            PreparedStatement preparedStatement = con.prepareStatement(insertQuery);
            int i = 0;
            for (Entry entry : testResults.entrySet()) {
                preparedStatement.setString(1, uuid);
                preparedStatement.setString(2, (String) entry.getKey());
                preparedStatement.setFloat(3, (Float) entry.getValue());
                preparedStatement.addBatch();
                if (++i == 500) {
                    preparedStatement.executeBatch();
                    System.out.println("Inserted 500 records successfully.");
                    preparedStatement = con.prepareStatement(insertQuery);
                    i = 0;
                }
            }
            int[] batchResult = new int[0];
            if (i > 0) batchResult = preparedStatement.executeBatch();
            System.out.println("Inserted " + batchResult.length + " records successfully.");
        } catch (SQLException throwables) {
            throwables.printStackTrace();
        }
    }

    public static void updatePrTriggerCount(PR pr, int count, int preCount, String fileName) throws Exception {
        String sql;
        if (count == 0 && preCount > 0) {
            while (count != preCount) {
                List<Map<String, String>> result = JSYDBUtils.query("select " + fileName + " from prIdMessage_new WHERE prid=" + pr.getPrId(), fileName);
                count = Integer.parseInt(result.get(0).get(fileName));
                sql = "UPDATE prIdMessage_new SET " + fileName + "=" + 1 + " WHERE prid=" + pr.getPrId();
                JSYDBUtils.updateData(sql);
            }

        } else if (count > 0 && preCount != count) {
            while (count != preCount) {
                List<Map<String, String>> result = JSYDBUtils.query("select " + fileName + " from prIdMessage_new WHERE prid=" + pr.getPrId(), fileName);
                count = Integer.parseInt(result.get(0).get(fileName));
                sql = "UPDATE prIdMessage_new SET " + fileName + "=" + preCount + " WHERE prid=" + pr.getPrId();
                JSYDBUtils.updateData(sql);
            }

        }
    }

    public static void close(ResultSet rs) {
        close(null, null, rs);
    }

    public static void close(Connection con, Statement stat) {
        close(con, stat, null);
    }

    public static void close(Connection con, Statement stat, ResultSet rs) {
        if (con != null) {
            try {
                con.close();
            } catch (SQLException e) {
                e.printStackTrace();
            }
        }

        if (stat != null) {
            try {
                stat.close();
            } catch (SQLException e) {
                e.printStackTrace();
            }
        }

        if (rs != null) {
            try {
                rs.close();
            } catch (SQLException e) {
                e.printStackTrace();
            }
        }
    }

    public static void close() {
        if (conn != null) {
            try {
                conn.close();
            } catch (SQLException e) {
                e.printStackTrace();
            }
        }
    }


    public static boolean isExitBenchMarkResult(PR pr) throws Exception {
        List<Map<String, String>> result = JSYDBUtils.query("select count(*) as c from benchmarkResultMetaData where codeType=\"" + pr.getCodeType() + "\" and prid=" + pr.getPrId() + ";", "c");
        int count = Integer.parseInt(result.get(0).get("c"));
        return count != 0;
    }

}
