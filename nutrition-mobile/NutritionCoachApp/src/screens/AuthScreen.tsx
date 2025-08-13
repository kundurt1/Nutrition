import React, { useState } from 'react';
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    SafeAreaView,
    Alert,
    StyleSheet,
    KeyboardAvoidingView,
    Platform,
} from 'react-native';
import { useAuth } from '../contexts/AuthContext';
import { colors } from '../styles/colors';

const AuthScreen = () => {
    const [email, setEmail] = useState('');
    const { signIn, loading } = useAuth();

    const handleSignIn = async () => {
        if (!email.trim()) {
            Alert.alert('Error', 'Please enter an email address');
            return;
        }

        try {
            await signIn(email);
        } catch (error) {
            Alert.alert('Error', 'Failed to sign in. Please try again.');
        }
    };

    return (
        <SafeAreaView style={styles.container}>
            <KeyboardAvoidingView
                style={styles.keyboardView}
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            >
                <View style={styles.content}>
                    {/* App Header */}
                    <View style={styles.header}>
                        <Text style={styles.appName}>Nutrition Coach</Text>
                        <Text style={styles.subtitle}>Your personal AI nutrition assistant</Text>
                    </View>

                    {/* Sign In Form */}
                    <View style={styles.formContainer}>
                        <Text style={styles.formTitle}>Create an account</Text>
                        <Text style={styles.formSubtitle}>Enter your email to sign up for this app</Text>

                        <View style={styles.inputContainer}>
                            <Text style={styles.inputLabel}>Email</Text>
                            <TextInput
                                style={styles.input}
                                value={email}
                                onChangeText={setEmail}
                                placeholder="Enter your email"
                                keyboardType="email-address"
                                autoCapitalize="none"
                                autoCorrect={false}
                            />
                        </View>

                        <TouchableOpacity
                            style={[styles.primaryButton, loading && styles.disabledButton]}
                            onPress={handleSignIn}
                            disabled={loading}
                        >
                            <Text style={styles.primaryButtonText}>
                                {loading ? 'Signing In...' : 'Continue'}
                            </Text>
                        </TouchableOpacity>

                        {/* Social Login Options */}
                        <View style={styles.divider}>
                            <View style={styles.dividerLine} />
                            <Text style={styles.dividerText}>OR CONTINUE WITH</Text>
                            <View style={styles.dividerLine} />
                        </View>

                        <TouchableOpacity style={styles.googleButton}>
                            <Text style={styles.socialButtonText}>Continue with Google</Text>
                        </TouchableOpacity>

                        <TouchableOpacity style={styles.appleButton}>
                            <Text style={styles.appleButtonText}>Continue with Apple</Text>
                        </TouchableOpacity>

                        {/* Terms */}
                        <Text style={styles.termsText}>
                            By clicking continue, you agree to our{' '}
                            <Text style={styles.termsLink}>Terms of Service</Text>
                            {' '}and{' '}
                            <Text style={styles.termsLink}>Privacy Policy</Text>
                        </Text>
                    </View>
                </View>
            </KeyboardAvoidingView>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.background,
    },
    keyboardView: {
        flex: 1,
    },
    content: {
        flex: 1,
        paddingHorizontal: 24,
        justifyContent: 'center',
    },
    header: {
        alignItems: 'center',
        marginBottom: 48,
    },
    appName: {
        fontSize: 32,
        fontWeight: 'bold',
        color: colors.text,
        marginBottom: 8,
    },
    subtitle: {
        fontSize: 16,
        color: colors.textSecondary,
        textAlign: 'center',
    },
    formContainer: {
        backgroundColor: colors.cardBackground,
        borderRadius: 16,
        padding: 24,
        shadowColor: '#000',
        shadowOffset: {
            width: 0,
            height: 2,
        },
        shadowOpacity: 0.1,
        shadowRadius: 8,
        elevation: 4,
    },
    formTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: colors.text,
        textAlign: 'center',
        marginBottom: 8,
    },
    formSubtitle: {
        fontSize: 14,
        color: colors.textSecondary,
        textAlign: 'center',
        marginBottom: 32,
    },
    inputContainer: {
        marginBottom: 24,
    },
    inputLabel: {
        fontSize: 14,
        fontWeight: '600',
        color: colors.text,
        marginBottom: 8,
    },
    input: {
        height: 48,
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: 8,
        paddingHorizontal: 16,
        fontSize: 16,
        color: colors.text,
        backgroundColor: colors.background,
    },
    primaryButton: {
        height: 48,
        backgroundColor: colors.text,
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: 24,
    },
    disabledButton: {
        opacity: 0.6,
    },
    primaryButtonText: {
        color: colors.textInverse,
        fontSize: 16,
        fontWeight: '600',
    },
    divider: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 24,
    },
    dividerLine: {
        flex: 1,
        height: 1,
        backgroundColor: colors.border,
    },
    dividerText: {
        fontSize: 12,
        color: colors.textLight,
        marginHorizontal: 16,
    },
    googleButton: {
        height: 48,
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: 16,
        backgroundColor: colors.cardBackground,
    },
    appleButton: {
        height: 48,
        backgroundColor: colors.text,
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: 24,
    },
    socialButtonText: {
        fontSize: 16,
        fontWeight: '600',
        color: colors.text,
    },
    appleButtonText: {
        fontSize: 16,
        fontWeight: '600',
        color: colors.textInverse,
    },
    termsText: {
        fontSize: 12,
        color: colors.textLight,
        textAlign: 'center',
        lineHeight: 18,
    },
    termsLink: {
        color: colors.primary,
        textDecorationLine: 'underline',
    },
});

export default AuthScreen;