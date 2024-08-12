package ci.benchMark.comparator;

/**
 * @author sunmuchao
 * @date 2024/4/26 2:17 下午
 */

//比较器：
// 例如完成a用例的x版本和y版本的比较，这个x、y可以是当前pr和历史pr、 可以是polars 和 其他数据库 、也可以是c++ 和 java等
public interface BenchmarkComparator {
    //A 和 B代表对应表单的索引方式，例如PR的对比就是prid作为索引
    public void compare(String A, String B);
}
