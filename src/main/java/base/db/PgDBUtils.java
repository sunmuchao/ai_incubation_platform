package base.db;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

public class PgDBUtils {
    private Connection conn;
    private Statement stmt;
    public PgDBUtils(String url, String username, String password){
        try {
            Class.forName("org.postgresql.Driver");
            conn = DriverManager.getConnection(url, username, password);
            conn.setAutoCommit(false);
            stmt = conn.createStatement();
        } catch (Exception e) {
            e.printStackTrace();
            System.err.println(e.getClass().getName()+": "+e.getMessage());
            System.exit(0);
        }
    }

    public void insertData(StringBuffer sql){
        try {
            System.out.println(sql);
            stmt.executeUpdate(String.valueOf(sql));
            conn.commit();
        } catch (Exception e) {
            System.err.println( e.getClass().getName()+": "+ e.getMessage() );
            System.exit(0);
        }
    }

    public ResultSet selectData(String sql){
        ResultSet resultSet = null;
        try {
            System.out.println(sql);
            resultSet = stmt.executeQuery(sql);
            conn.commit();
        } catch (Exception e) {
            System.err.println( e.getClass().getName()+": "+ e.getMessage() );
            System.exit(0);
        }finally {
            return resultSet;
        }
    }

    public void closeDBConn() throws SQLException {
        stmt.close();
        conn.commit();
        conn.close();
    }
}

