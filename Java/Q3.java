public class Q3 {
    public static void rightPyramidPattern(int n) {
        for (int i = 0; i < 2 * n - 1; i++) {
            if (i < n) {
                for (int j = 0; j <= i; j++) {
                    System.out.print(2 * j + 1 + " ");
                }
            } else {
                for (int j = 0; j < 2 * n - 1 - i; j++) {
                    System.out.print(2 * j + 1 + " ");
                }
            }
            System.out.println();
        }
    }
    public static void main(String args[]) {
      rightPyramidPattern(3);
    }
}