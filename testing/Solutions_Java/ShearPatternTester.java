import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

public class ShearPatternTester {

    // Define the shear_pattern method
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

    // Define a method to check if the actual output matches the expected output
    public static boolean checkTestCase(int n, String expected) {
        // Capture the actual output in a ByteArrayOutputStream
        ByteArrayOutputStream actualOutputStream = new ByteArrayOutputStream();
        PrintStream actualPrintStream = new PrintStream(actualOutputStream);
        PrintStream originalOut = System.out;
        System.setOut(actualPrintStream);

        // Call the shear_pattern method with the given input
        shearPattern(n);

        // Reset System.out
        System.out.flush();
        System.setOut(originalOut);

        // Convert the actual output to a string
        String actual = actualOutputStream.toString();
        String expectedTrimmed = expected;

        // Check if the actual output matches the expected output
        boolean result =  actual.equals(expectedTrimmed);
        if(!result){
                System.out.println("Expected Output\n"+ expectedTrimmed);
                System.out.println("Your Output\n"+ actual);
            }
        return result;
    }

    public static void main(String[] args) {
        // Define test cases as an array of arrays
        String[][] testCases = {
            { "1", "1 \n" },
            { "2", "1 3 \n 1 3 \n" },
            { "5", "1 3 5 7 9 \n 1 3 5 7 9 \n  1 3 5 7 9 \n   1 3 5 7 9 \n    1 3 5 7 9 \n" },
            { "7", "1 3 5 7 9 11 13 \n 1 3 5 7 9 11 13 \n  1 3 5 7 9 11 13 \n   1 3 5 7 9 11 13 \n    1 3 5 7 9 11 13 \n     1 3 5 7 9 11 13 \n      1 3 5 7 9 11 13 \n" }
            // Add more test cases as needed
        };

        // Test the shear_pattern method with each test case
        for (String[] testCase : testCases) {
            int input = Integer.parseInt(testCase[0]);
            String expectedOutput = testCase[1];

            // Check if the actual output matches the expected output
            boolean result = checkTestCase(input, expectedOutput);

            // Print the test result
            System.out.println("Test case for n = " + input + ": " + (result ? "Passed\n" : "Failed\n"));
        }
    }
}
