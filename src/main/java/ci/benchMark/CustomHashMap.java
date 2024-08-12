package ci.benchMark;

import java.util.*;

public class CustomHashMap {
    HashMap<String, Integer> result;
    HashSet<String> set;
    int size;
    CustomHashMap(int size) {
        result = new HashMap();
        set = new HashSet();
        this.size = size;
    }

    public void putAll(List<String> list){
        for (String s : list) {
            if (result.containsKey(s)) {
                result.put(s, result.get(s) + 1);
            } else {
                result.put(s, 1);
            }
        }
    }

    public HashSet<String> getIntersection() {
        for (Map.Entry<String, Integer> entry : result.entrySet()) {
            if (entry.getValue() == size) {
                set.add(entry.getKey());
            }
        }
        return set;
    }
}
