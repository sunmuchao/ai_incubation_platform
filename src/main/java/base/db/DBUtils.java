package base.db;

import com.alibaba.druid.pool.DruidDataSource;

import javax.sql.DataSource;
import java.sql.*;
import java.util.*;

//针对bi_performance_auto的工具类
public class DBUtils {
    private static DruidDataSource dataSource;
    static {
        try {
            dataSource = new DruidDataSource();
            dataSource.setDriverClassName("com.mysql.jdbc.Driver");
            dataSource.setUrl("jdbc:mysql://47.102.211.0:3306/bi_performance_auto?useUnicode=true&characterEncoding=utf8&autoReconnect=true&useSSL=false&connectTimeOut=60000&socketTimeOut=60000");
            dataSource.setUsername("fanruan");
            dataSource.setPassword("Fanruan");
            dataSource.setMaxActive(50);
            dataSource.setMinIdle(5);
            dataSource.setMaxWait(5000);
            dataSource.setConnectionErrorRetryAttempts(3);
            dataSource.init();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static DataSource getDataSource(){
        return dataSource;
    }

    public static Connection getConnection(){
        Connection conn = null;
        try { //从连接池中获取连接对象
            conn = dataSource.getConnection();
        } catch (SQLException e) {
            e.printStackTrace();
        }
        return conn;
    }

    //适配sun.sun之前写的
    public static List<String> readBranchName(){
        List<String> branchNameList = new ArrayList<>();
        List<Map<String, String>> results = query("select branchName from ci;", "branchName");
        for(Map<String,String> map : results){
            branchNameList.add(map.get("branchName"));
        }
        return branchNameList;
    }

    /**
     * 查询*
     * @param sql sql语句
     * @param parameters 想要查到的数据列
     * @return 每一行的数据列通过键值对的方式储存到map中，通过list存放多行
     */
    public static List<Map<String,String>> query(String sql,String...parameters) {
        System.out.println(sql);
        Connection con = null;
        PreparedStatement pst = null;
        ResultSet rs = null;
        List<Map<String,String>> result = new ArrayList<>();
        try {
            con = dataSource.getConnection();
            pst = con.prepareStatement(sql);
            pst.setQueryTimeout(60);
            rs = pst.executeQuery();
            while (rs.next()){
                Map<String,String> map = new HashMap<>();
                if (parameters.length>0){
                    for (String parameter:parameters){
                        String value = rs.getString(parameter);
                        map.put(parameter,value);
                    }
                }
                result.add(map);
            }
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            close(con, pst,rs);
        }

        return result;
    }


    /**
     * 执行更新或新增的sql*
     * @param sql sql语句
     * @return 返回改变的行数
     */
    public static int updateData(String sql) {
        System.out.println(sql);
        int count = 0;
        Connection con = null;
        PreparedStatement pst = null;
        try{
            con = dataSource.getConnection();
            pst = con.prepareStatement(sql);
            pst.setQueryTimeout(60);
            count = pst.executeUpdate();
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            close(con,pst);
        }

        return count;
    }

    public static void close(ResultSet rs){close(null,null,rs);}

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




}
