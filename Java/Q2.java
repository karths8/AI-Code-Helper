public class Q2 {
    public static void shearPattern(int n) {
        for (int i = 0; i < n; i++) {
            for (int k = 0; k < i; k++) {
                System.out.print(" ");
            }
            for (int j = 1; j <= n; j++) {
                System.out.print(2 * j - 1 + " ");
            }
            System.out.println();
        }
    }
    public static void main(String args[]) {
      shearPattern(5);
    }
}