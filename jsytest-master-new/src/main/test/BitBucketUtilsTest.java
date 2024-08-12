import base.third.bitBucket.BitBucketUtils;
import org.junit.Assert;
import org.junit.Test;

/**
 * @author sunmuchao
 * @date 2024/5/10 9:55 上午
 */
public class BitBucketUtilsTest {
    @Test
    public void testIsOnlyHihidataChange(){
        String filePath = "/Users/sunmuchao/Downloads/polars-4761.patch";
        Boolean b = BitBucketUtils.isOnlyHihidataChange(filePath);
        Assert.assertFalse(b);
    }
}
