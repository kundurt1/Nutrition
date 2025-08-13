import React, { useState } from 'react';
import {
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    TextInput,
    SafeAreaView,
    StyleSheet,
    Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../styles/colors';

interface GroceryItem {
    id: number;
    name: string;
    category: string;
    completed: boolean;
}

const GroceryListScreen = () => {
    const [groceryItems, setGroceryItems] = useState<GroceryItem[]>([
        { id: 1, name: 'Chicken breast', category: 'Proteins', completed: false },
        { id: 2, name: 'Pesto sauce', category: 'Proteins', completed: false },
        { id: 3, name: 'Fresh basil', category: 'Produce', completed: true },
        { id: 4, name: 'Parmesan cheese', category: 'Grains and carbs', completed: false },
        { id: 5, name: 'Pasta', category: 'Dairy & Alternatives', completed: false },
        { id: 6, name: 'Olive oil', category: 'Pantry and Staples', completed: false },
        { id: 7, name: 'Frozen vegetables', category: 'Frozen and Misc', completed: false },
    ]);

    const [newItemText, setNewItemText] = useState('');
    const [showAddItem, setShowAddItem] = useState(false);

    const categories = [
        'Proteins',
        'Produce',
        'Grains and carbs',
        'Dairy & Alternatives',
        'Pantry and Staples',
        'Frozen and Misc'
    ];

    const toggleItem = (id: number) => {
        setGroceryItems(items =>
            items.map(item =>
                item.id === id ? { ...item, completed: !item.completed } : item
            )
        );
    };

    const addItem = (category: string) => {
        if (!newItemText.trim()) {
            Alert.alert('Error', 'Please enter an item name');
            return;
        }

        const newItem: GroceryItem = {
            id: Date.now(),
            name: newItemText.trim(),
            category,
            completed: false,
        };

        setGroceryItems(items => [...items, newItem]);
        setNewItemText('');
        setShowAddItem(false);
    };

    const removeItem = (id: number) => {
        setGroceryItems(items => items.filter(item => item.id !== id));
    };

    const getItemsByCategory = (category: string) => {
        return groceryItems.filter(item => item.category === category);
    };

    const CategorySection = ({ category }: { category: string }) => {
        const categoryItems = getItemsByCategory(category);

        if (categoryItems.length === 0) return null;

        return (
            <View style={styles.categorySection}>
                <Text style={styles.categoryTitle}>{category}</Text>
                {categoryItems.map(item => (
                    <View key={item.id} style={styles.groceryItem}>
                        <TouchableOpacity
                            style={[styles.checkbox, item.completed && styles.checkboxCompleted]}
                            onPress={() => toggleItem(item.id)}
                        >
                            {item.completed && <Ionicons name="checkmark" size={16} color={colors.textInverse} />}
                        </TouchableOpacity>

                        <Text style={[
                            styles.itemName,
                            item.completed && styles.itemNameCompleted
                        ]}>
                            {item.name}
                        </Text>

                        <TouchableOpacity
                            style={styles.removeButton}
                            onPress={() => removeItem(item.id)}
                        >
                            <Ionicons name="close" size={20} color={colors.textLight} />
                        </TouchableOpacity>
                    </View>
                ))}
            </View>
        );
    };

    const AddItemModal = () => (
        <View style={styles.addItemContainer}>
            <Text style={styles.addItemTitle}>Add Item</Text>
            <TextInput
                style={styles.addItemInput}
                value={newItemText}
                onChangeText={setNewItemText}
                placeholder="Enter item name"
                autoFocus
            />

            <Text style={styles.categorySelectTitle}>Select Category:</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryScroll}>
                {categories.map(category => (
                    <TouchableOpacity
                        key={category}
                        style={styles.categoryButton}
                        onPress={() => addItem(category)}
                    >
                        <Text style={styles.categoryButtonText}>{category}</Text>
                    </TouchableOpacity>
                ))}
            </ScrollView>

            <TouchableOpacity
                style={styles.cancelButton}
                onPress={() => {
                    setShowAddItem(false);
                    setNewItemText('');
                }}
            >
                <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>
        </View>
    );

    return (
        <SafeAreaView style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <Text style={styles.headerTitle}>Grocery List</Text>
            </View>

            <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
                {/* Categories */}
                {categories.map(category => (
                    <CategorySection key={category} category={category} />
                ))}

                {/* Add Item Section */}
                {showAddItem ? (
                    <AddItemModal />
                ) : (
                    <TouchableOpacity
                        style={styles.addButton}
                        onPress={() => setShowAddItem(true)}
                    >
                        <Ionicons name="add" size={24} color={colors.textInverse} />
                        <Text style={styles.addButtonText}>Add Item</Text>
                    </TouchableOpacity>
                )}

                {/* Action Buttons */}
                <View style={styles.actionButtons}>
                    <TouchableOpacity style={styles.doorDashButton}>
                        <Text style={styles.actionButtonText}>Place Doordash order</Text>
                    </TouchableOpacity>

                    <TouchableOpacity style={styles.instacartButton}>
                        <Text style={styles.actionButtonText}>Place Instacart order</Text>
                    </TouchableOpacity>
                </View>
            </ScrollView>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.background,
    },
    header: {
        paddingTop: 20,
        paddingBottom: 24,
        paddingHorizontal: 16,
        alignItems: 'center',
    },
    headerTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: colors.text,
    },
    scrollView: {
        flex: 1,
        paddingHorizontal: 16,
    },
    categorySection: {
        marginBottom: 24,
    },
    categoryTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: colors.text,
        marginBottom: 12,
    },
    groceryItem: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: colors.cardBackground,
        borderRadius: 12,
        padding: 16,
        marginBottom: 8,
        shadowColor: '#000',
        shadowOffset: {
            width: 0,
            height: 1,
        },
        shadowOpacity: 0.05,
        shadowRadius: 2,
        elevation: 1,
    },
    checkbox: {
        width: 24,
        height: 24,
        borderRadius: 12,
        borderWidth: 2,
        borderColor: colors.border,
        marginRight: 12,
        justifyContent: 'center',
        alignItems: 'center',
    },
    checkboxCompleted: {
        backgroundColor: colors.success,
        borderColor: colors.success,
    },
    itemName: {
        flex: 1,
        fontSize: 16,
        color: colors.text,
    },
    itemNameCompleted: {
        textDecorationLine: 'line-through',
        color: colors.textLight,
    },
    removeButton: {
        padding: 4,
    },
    addButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: colors.primary,
        borderRadius: 12,
        padding: 16,
        marginBottom: 24,
    },
    addButtonText: {
        color: colors.textInverse,
        fontSize: 16,
        fontWeight: '600',
        marginLeft: 8,
    },
    addItemContainer: {
        backgroundColor: colors.cardBackground,
        borderRadius: 16,
        padding: 20,
        marginBottom: 24,
        shadowColor: '#000',
        shadowOffset: {
            width: 0,
            height: 2,
        },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 2,
    },
    addItemTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: colors.text,
        marginBottom: 16,
    },
    addItemInput: {
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: 8,
        padding: 12,
        fontSize: 16,
        color: colors.text,
        backgroundColor: colors.background,
        marginBottom: 16,
    },
    categorySelectTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: colors.text,
        marginBottom: 12,
    },
    categoryScroll: {
        marginBottom: 16,
    },
    categoryButton: {
        backgroundColor: colors.primary,
        paddingHorizontal: 16,
        paddingVertical: 8,
        borderRadius: 20,
        marginRight: 8,
    },
    categoryButtonText: {
        color: colors.textInverse,
        fontSize: 14,
        fontWeight: '500',
    },
    cancelButton: {
        alignItems: 'center',
        padding: 12,
    },
    cancelButtonText: {
        color: colors.textSecondary,
        fontSize: 16,
    },
    actionButtons: {
        marginBottom: 32,
    },
    doorDashButton: {
        backgroundColor: colors.text,
        borderRadius: 12,
        padding: 16,
        alignItems: 'center',
        marginBottom: 12,
    },
    instacartButton: {
        backgroundColor: colors.text,
        borderRadius: 12,
        padding: 16,
        alignItems: 'center',
    },
    actionButtonText: {
        color: colors.textInverse,
        fontSize: 16,
        fontWeight: '600',
    },
});

export default GroceryListScreen;